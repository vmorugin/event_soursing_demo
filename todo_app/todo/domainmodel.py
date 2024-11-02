from __future__ import annotations

from enum import Enum
import typing as t
from functools import (
    singledispatch,
)
from uuid import (
    UUID,
    uuid5,
    NAMESPACE_URL,
)

from pydantic import (
    BaseModel,
    Field,
)
from todo.seedwork import (
    DomainEvent,
    TodoDomainEvent,
    Aggregate,
    Snapshot,
    create_timestamp,
)

TAggregate = t.TypeVar("TAggregate", bound=Aggregate)
MutatorFunction = t.Callable[..., t.Optional[TAggregate]]


def aggregate_projector(
        mutator: MutatorFunction[TAggregate],
) -> t.Callable[[TAggregate | None, t.Iterable[DomainEvent]], TAggregate | None]:
    def project_aggregate(
            aggregate: TAggregate | None, events: t.Iterable[DomainEvent]
    ) -> TAggregate | None:
        for event in events:
            aggregate = mutator(event, aggregate)
        return aggregate

    return project_aggregate


class ItemStatus(str, Enum):
    CREATED = 'CREATED'
    DONE = 'DONE'


class Created(TodoDomainEvent):
    title: str


class ItemAdded(TodoDomainEvent):
    item: Item

class ItemRemoved(TodoDomainEvent):
    item_id: UUID


class ItemMarkedDown(TodoDomainEvent):
    item_id: UUID


class Item(BaseModel):
    title: str
    status: str

    def mark_done(self):
        self.status = 'DONE'

    def create_id(self):
        return uuid5(NAMESPACE_URL, f'/todo/item/{self.title.upper()}')


class Todo(Aggregate):
    title: str
    items: dict[UUID, Item] = Field(default_factory=dict)

    @classmethod
    def create(cls, title: str) -> Created:
        return Created(
            originator_id=cls.create_id(title),
            originator_version=1,
            timestamp=create_timestamp(),
            title=title,
        )

    @classmethod
    def create_id(cls, title: str):
        return uuid5(NAMESPACE_URL, f'/todo/{title.upper()}')

    def collect_items(self) -> t.Iterable[Item]:
        return list(self.items.values())


    def add_item(self, title: str) -> ItemAdded:
        return ItemAdded(
            originator_id=self.id,
            originator_version=self.version + 1,
            timestamp=create_timestamp(),
            item=Item(title=title, status=ItemStatus.CREATED),
        )

    def remove_item(self, item_id: UUID) -> ItemRemoved:
        return ItemRemoved(
            originator_id=self.id,
            originator_version=self.version + 1,
            timestamp=create_timestamp(),
            item_id=item_id,
        )

    def mark_done(self, item_id: UUID) -> ItemMarkedDown:
        return ItemMarkedDown(
            originator_id=self.id,
            originator_version=self.version + 1,
            timestamp=create_timestamp(),
            item_id=item_id,
        )


@singledispatch
def mutate(event: DomainEvent, aggregate: Todo | None) -> Todo:
    ...


@mutate.register
def _(event: Created, _: None) -> Todo:
    return Todo(
        id=event.originator_id,
        version=event.originator_version,
        created_on=event.timestamp,
        modified_on=event.timestamp,
        title=event.title,
    )


@mutate.register
def _(event: ItemAdded, todo: Todo) -> Todo:
    todo = Todo(
        id=todo.id,
        version=event.originator_version,
        created_on=todo.created_on,
        modified_on=event.timestamp,
        title=todo.title,
        items=todo.items | {event.item.create_id(): event.item}
    )
    return todo

@mutate.register
def _(event: ItemRemoved, todo: Todo) -> Todo:
    todo = Todo(
        id=todo.id,
        version=event.originator_version,
        created_on=todo.created_on,
        modified_on=event.timestamp,
        title=todo.title,
        items=todo.items,
    )
    if event.item_id in todo.items:
        todo.items.pop(event.item_id)
    return todo

@mutate.register
def _(event: ItemMarkedDown, todo: Todo) -> Todo:
    todo = Todo(
        id=todo.id,
        version=event.originator_version,
        created_on=todo.created_on,
        modified_on=event.timestamp,
        title=todo.title,
        items=todo.items,
    )
    todo.items[event.item_id].mark_done()
    return todo


@mutate.register
def _(event: Snapshot, _: None):
    return Todo(
        id=event.state["id"],
        version=event.state["version"],
        created_on=event.state["created_on"],
        modified_on=event.state["modified_on"],
        title=event.state["title"],
        items=event.state["items"],
    )


project_todo = aggregate_projector(mutate)
