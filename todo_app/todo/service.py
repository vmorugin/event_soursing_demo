from functools import singledispatchmethod
from uuid import UUID

from todo.abstractions import (
    ITodoApp,
    ILock,
)
from todo.seedwork import DomainCommand


class CreateTodoCmd(DomainCommand):
    title: str


class AddItemCmd(DomainCommand):
    todo_id: UUID
    title: str


class TodoService:
    def __init__(self, todo_app: ITodoApp, lock: ILock):
        self._todo = todo_app
        self._lock = lock

    @singledispatchmethod
    def handle(self, command: DomainCommand, *args, **kwargs):
        ...

    @handle.register
    def _(self, command: CreateTodoCmd):
        with self._lock(f'todo-{command.title}'):
            todo_id = self._todo.create_todo(command.title)
        return todo_id

    @handle.register
    def _(self, command: AddItemCmd):
        with self._lock(f'todo-{command.todo_id}'):
            item_id = self._todo.add_item(command.todo_id, title=command.title)
        return item_id

