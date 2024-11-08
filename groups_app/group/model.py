from functools import singledispatch
from typing import (
    TypeVar,
    Iterable,
)
from uuid import (
    UUID,
    uuid4,
)
from d3m.core import (
    AbstractEvent,
    MessageName,
)
from d3m.core.abstractions import AbstractEventMeta

from d3m.domain import (
    RootEntity,
    get_event_class,
)
from d3m.domain.bases import (
    BaseDomainMessage,
    BaseDomainMessageMeta,
)
from pydantic import (
    BaseModel,
    Field,
)

def set_version(entity: RootEntity, version: int):
    """
    Set the version of the root entity

    Attributes:
        entity (RootEntity): The root entity object whose version needs to be set.

    """
    if isinstance(entity.__pydantic_private__, dict):
        entity.__pydantic_private__["_RootEntity__version"] = version

ReferenceType = TypeVar("ReferenceType", bound=UUID)

class _DomainEventMeta(BaseDomainMessageMeta, AbstractEventMeta):
    def __init__(cls, name, bases, namespace, *, domain: str | None = None):
        super().__init__(name, bases, namespace, domain=domain)
        if domain is None and cls.__module__ != __name__:
            try:
                _ = cls.__domain_name__
            except AttributeError:
                raise ValueError(
                    f"required set domain name for event '{cls.__module__}.{cls.__name__}'"
                )


class DomainEvent(BaseDomainMessage, AbstractEvent, metaclass=_DomainEventMeta):
    reference: UUID
    version: int

class GroupDomainEvent(DomainEvent, domain='group'):
    ...


class GroupCreated(GroupDomainEvent):
    name: str


class GroupRenamed(GroupDomainEvent):
    name: str


class GroupMember(BaseModel):
    reference: UUID
    name: str


class GroupMemberAdded(GroupDomainEvent):
    member: GroupMember


class GroupReassigned(GroupDomainEvent):
    parent_id: ReferenceType


class GroupState(BaseModel):
    name: str
    parent_id: ReferenceType | None = None
    members: dict[ReferenceType, GroupMember] = Field(default_factory=dict)

    class Config:
        frozen = True


class Group(RootEntity, domain='group'):
    state: GroupState

    def __init__(self, **data):
        super().__init__(**data)
        self._events: list[AbstractEvent] = list()

    @classmethod
    def create(cls, name: str) -> 'Group':
        event = GroupCreated(
            reference=uuid4(),
            version=1,
            name=name
        )
        group = mutate(event, None)
        group._events.append(event)
        return group

    def rename(self, new_name: str):
        event = self.create_event(GroupRenamed.__name__, name=new_name)
        mutate(event, self)

    def add_member(self, name: str, reference: ReferenceType):
        member = GroupMember(name=name, reference=reference)
        event = self.create_event(GroupMemberAdded.__name__, member=member)
        mutate(event, self)

    def reassign(self, parent_id: ReferenceType):
        event = self.create_event(GroupReassigned.__name__, parent_id=parent_id)
        mutate(event, self)

    def create_event(self, __name: MessageName | str, /, **payload) -> DomainEvent:
        event_class = get_event_class(self.__domain_name__, __name)
        event = event_class(
            reference=self.__reference__,
            version=self.__version__ + 1,
            **payload,
        )
        self._events.append(event)
        return event

    def collect_events(self) -> Iterable[DomainEvent]:
        events = self._events
        self._events = []
        yield from events


@singledispatch
def mutate(event: AbstractEvent, _: None | Group) -> Group:
    raise RuntimeError(f"Unhandled event {event.__class__.__name__}")


@mutate.register
def _(event: GroupCreated, _: None) -> Group:
    group = Group(
        __reference__=event.reference,
        __version__=event.version,
        state=GroupState(name=event.name)
    )
    return group


@mutate.register
def _(event: GroupMemberAdded, aggregate: Group) -> Group:
    aggregate.state = GroupState(
        name=aggregate.state.name,
        parent_id=aggregate.state.parent_id,
        members=aggregate.state.members | {event.member.reference: event.member},
    )
    set_version(aggregate, event.version)
    return aggregate


@mutate.register
def _(event: GroupReassigned, aggregate: Group) -> Group:
    aggregate.state = GroupState(
        name=aggregate.state.name,
        members=aggregate.state.members,
        parent_id=event.parent_id,
    )
    set_version(aggregate, event.version)
    return aggregate


@mutate.register
def _(event: GroupRenamed, aggregate: Group) -> Group:
    aggregate.state = GroupState(
        name=event.name,
        parent_id=aggregate.state.parent_id,
        members=aggregate.state.members,
    )
    set_version(aggregate, event.version)
    return aggregate
