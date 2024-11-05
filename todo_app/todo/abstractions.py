import abc
from typing import ContextManager
from uuid import UUID

from todo.domainmodel import Todo


class ITodoApp(abc.ABC):
    @abc.abstractmethod
    def create_todo(self, title: str) -> UUID:
        ...

    @abc.abstractmethod
    def get_todo(self, todo_id: UUID) -> Todo:
        ...

    @abc.abstractmethod
    def add_item(self, todo_id: UUID, title: str):
        ...

    @abc.abstractmethod
    def remove_item(self, todo_id: UUID, item_id: UUID):
        ...

    @abc.abstractmethod
    def done_item(self, todo_id: UUID, item_id: UUID):
        ...


class ILock(ContextManager):

    @abc.abstractmethod
    def __call__(self, __lock_key: str = None):
        ...
