from typing import (
    Any,
    List,
)
from uuid import UUID

from eventsourcing.application import (
    Application,
)
from eventsourcing.domain import (
    MutableOrImmutableAggregate,
    DomainEventProtocol,
)
from eventsourcing.persistence import (
    IntegrityError,
    Mapper,
    Recording,
)

from todo.abstractions import ITodoApp
from todo.domainmodel import (
    Todo,
    project_todo,
)
from todo.seedwork import (
    Snapshot,
)
from todo.mappers import PydanticMapper


class TodoApp(ITodoApp, Application):
    is_snapshotting_enabled = True
    snapshot_class = Snapshot

    def create_todo(self, title: str) -> UUID:
        registered = Todo.create(title)
        try:
            self.save(registered)
            return registered.originator_id
        except IntegrityError:
            todo = self.repository.get(registered.originator_id, projector_func=project_todo)
            return todo.id

    def get_todo(self, todo_id: UUID) -> Todo:
        return self.repository.get(todo_id, projector_func=project_todo)

    def add_item(self, todo_id: UUID, title: str):
        todo: Todo = self.repository.get(todo_id, projector_func=project_todo)
        item_added = todo.add_item(title)
        self.save(item_added)
        return item_added.item.create_id()

    def remove_item(self, todo_id: UUID, item_id: UUID):
        todo = self.repository.get(todo_id, projector_func=project_todo)
        self.save(todo.remove_item(item_id))

    def done_item(self, todo_id: UUID, item_id: UUID):
        todo = self.repository.get(todo_id, projector_func=project_todo)
        self.save(todo.mark_done(item_id))

    def construct_mapper(self) -> Mapper:
        return self.factory.mapper(
            transcoder=self.construct_transcoder(),
            mapper_class=PydanticMapper,
        )

    def save(
            self,
            *objs: MutableOrImmutableAggregate | DomainEventProtocol | None,
            **kwargs: Any,
    ) -> List[Recording]:
        records = super().save(*objs, **kwargs)
        snapshot_interval = 100
        for record in records:
            if record.domain_event.originator_version % snapshot_interval == 0:
                self.take_snapshot(
                    record.domain_event.originator_id,
                    record.domain_event.originator_version,
                    projector_func=project_todo
                )
        return records
