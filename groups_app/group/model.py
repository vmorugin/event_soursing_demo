from __future__ import annotations
from typing import (
    TypeVar,
)
from uuid import (
    UUID,
    uuid4,
)
from pydantic import (
    BaseModel,
    Field,
)
from group.bases import (
    DomainEvent,
    RootEntity,
)

ReferenceType = TypeVar("ReferenceType", bound=UUID)


class GroupDomainEvent(DomainEvent, domain='group'):
    ...


class GroupCreated(GroupDomainEvent):
    name: str
    parent_id: UUID | None

    def mutate(self, _: None) -> Group:
        group = Group(
            __reference__=self.reference,
            __version__=self.version,
            state=GroupState(name=self.name, parent_id=self.parent_id)
        )
        return group


class GroupRenamed(GroupDomainEvent):
    name: str

    def apply(self, aggregate: RootEntity):
        aggregate.state = GroupState(
            name=self.name,
            parent_id=aggregate.state.parent_id,
            members=aggregate.state.members,
        )


class GroupMember(BaseModel):
    reference: UUID
    name: str


class GroupMemberAdded(GroupDomainEvent):
    member: GroupMember

    def apply(self, aggregate: Group) -> None:
        aggregate.state = GroupState(
            name=aggregate.state.name,
            parent_id=aggregate.state.parent_id,
            members=aggregate.state.members | {self.member.reference: self.member},
        )


class GroupReassigned(GroupDomainEvent):
    parent_id: ReferenceType

    def apply(self, aggregate: Group) -> None:
        aggregate.state = GroupState(
            name=aggregate.state.name,
            parent_id=self.parent_id,
            members=aggregate.state.members,
        )


class GroupState(BaseModel):
    name: str
    parent_id: ReferenceType | None = None
    members: dict[ReferenceType, GroupMember] = Field(default_factory=dict)

    class Config:
        frozen = True


class Group(RootEntity, domain='group'):
    state: GroupState

    @classmethod
    def create(cls, name: str, parent_id: ReferenceType | None) -> 'Group':
        event = GroupCreated(
            reference=uuid4(),
            version=1,
            name=name,
            parent_id=parent_id,
        )
        group = event.mutate(None)
        group._events.append(event)
        return group

    def rename(self, new_name: str):
        self.create_event(GroupRenamed.__name__, name=new_name)

    def add_member(self, name: str, reference: ReferenceType):
        member = GroupMember(name=name, reference=reference)
        self.create_event(GroupMemberAdded.__name__, member=member)

    def reassign(self, parent_id: ReferenceType):
        self.create_event(GroupReassigned.__name__, parent_id=parent_id)
