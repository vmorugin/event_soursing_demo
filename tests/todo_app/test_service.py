from unittest.mock import create_autospec
from uuid import (
    UUID,
)

import pytest

from todo.application import (
    TodoApp,
)
from todo.abstractions import ILock
from todo.service import (
    TodoService,
    CreateTodoCmd,
    AddItemCmd,
)


class TestService:
    @pytest.fixture
    def app(self):
        return TodoApp()

    @pytest.fixture
    def lock(self):
        mock_lock = create_autospec(ILock)
        return mock_lock()

    @pytest.fixture
    def service(self, app, lock):
        return TodoService(app, lock)

    def test_init(self):
        service = TodoService(todo_app=..., lock=...)
        assert service

    def test_create_todo(self, service):
        cmd = CreateTodoCmd(title='test')
        todo_id = service.handle(cmd)
        assert todo_id == UUID('b797acd1-93d9-5b44-80b6-9ce7d3228397')

    def test_add_item(self, service):
        todo_id = service.handle(CreateTodoCmd(title='test'))
        item_id = service.handle(AddItemCmd(todo_id=todo_id, title='Bread'))
        assert item_id == UUID('50d9ef4e-b0e8-5070-a9c6-be0abf7220a9')
