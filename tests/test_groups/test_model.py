from uuid import (
    uuid4,
    UUID,
)

import pytest

from group.model import (
    GroupCreated,
    GroupMember,
    Group,
)


class TestModel:
    @pytest.fixture
    def create_group(self):
        def wrapper(
                name: str = 'test',
                parent_id: UUID | None = None,
        ):
            return Group.create(name=name, parent_id=parent_id)

        return wrapper

    def test_create(self):
        group = Group.create(name='test', parent_id=None)
        state = group.state
        assert state.name == 'test'
        assert state.members == {}
        events = list(group.collect_events())
        event = events.pop()
        assert isinstance(event, GroupCreated)
        assert event.name == 'test'

    def test_create_with_parent_id(self):
        parent_id = uuid4()
        group = Group.create(name='test', parent_id=parent_id)
        state = group.state
        assert state.name == 'test'
        assert state.members == {}
        assert state.parent_id == parent_id
        events = list(group.collect_events())
        event = events.pop()
        assert isinstance(event, GroupCreated)
        assert event.name == 'test'

    def test_mutate(self):
        event = GroupCreated(
            reference=uuid4(),
            version=1,
            name='test',
            parent_id=None,
        )
        group = event.mutate(None)
        assert isinstance(group, Group)
        assert group.__version__ == 1
        assert group.__reference__ == event.reference
        assert group.state.name == 'test'

    def test_rename(self, create_group):
        group = create_group()
        group.rename("new-group")
        assert group.state.name == 'new-group'

    def test_add_member(self, create_group):
        group = create_group()
        member = create_group()
        group.add_member(name=member.state.name, reference=member.__reference__)
        assert list(group.state.members.values()) == [
            GroupMember(name=member.state.name, reference=member.__reference__)]

    def test_load_from_events(self, create_group):
        group = create_group(parent_id=uuid4())
        group.rename('new-test')
        group.add_member(name='new-member', reference=uuid4())
        group.reassign(uuid4())
        copy = None
        for event in group.collect_events():
            copy = event.mutate(copy)

        assert copy == group
        assert copy.state == group.state
        assert copy.__reference__ == group.__reference__
        assert copy.__version__ == group.__version__ == 4

    def test_reassign(self, create_group):
        group = create_group()
        parent = create_group()
        group.reassign(parent.__reference__)
        parent.add_member(reference=group.__reference__, name=group.state.name)
