from uuid import (
    uuid4,
)
from group.model import (
    GroupCreated,
    GroupMember,
    Group,
    mutate,
)


def test_init():
    group = Group.create(name='test')
    state = group.state
    assert state.name == 'test'
    assert state.members == {}
    events = list(group.collect_events())
    event = events.pop()
    assert isinstance(event, GroupCreated)
    assert event.name == 'test'


def test_mutate():
    event = GroupCreated(
        reference=uuid4(),
        version=1,
        name='test'
    )
    group = mutate(event, None)
    assert isinstance(group, Group)
    assert group.__version__ == 1
    assert group.__reference__ == event.reference
    assert group.state.name == 'test'


def test_rename():
    group = Group.create(name='test')
    group.rename("new-group")
    assert group.state.name == 'new-group'


def test_add_member():
    group = Group.create('test')
    member = Group.create('test')
    group.add_member(name=member.state.name, reference=member.__reference__)
    assert list(group.state.members.values()) == [GroupMember(name=member.state.name, reference=member.__reference__)]


def test_load_from_events():
    group = Group.create(name='test')
    group.rename('new-test')
    group.add_member(name='new-member', reference=uuid4())
    group.reassign(uuid4())
    copy = None
    for event in group.collect_events():
        copy = mutate(event, copy)

    assert copy == group
    assert copy.state == group.state
    assert copy.__reference__ == group.__reference__
    assert copy.__version__ == group.__version__ == 4


def test_reassign():
    group = Group.create('name')
    parent = Group.create('name')
    group.reassign(parent.__reference__)
    parent.add_member(reference=group.__reference__, name=group.state.name)
