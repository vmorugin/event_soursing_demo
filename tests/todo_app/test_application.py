import uuid
from uuid import UUID

import pytest
from eventsourcing.application import (
    Application,
    AggregateNotFoundError,
)

from todo.application import (
    TodoApp,
    ITodoApp,
)
from todo.domainmodel import (
    Item,
    ItemStatus,
)


class TestApplication:
    @pytest.fixture
    def application(self):
        return TodoApp()

    def test_init(self, application):
        assert isinstance(application, Application)
        assert isinstance(application, ITodoApp)

    def test_create_todo(self, application):
        todo_id = application.create_todo("Orders")
        assert todo_id == UUID('0f022c8e-ab7c-5cf5-8afb-9b91b30dcd3e')

    def test_create_exists_todo(self, application):
        assert application.create_todo('Orders') == application.create_todo("Orders")

    def test_get_todo(self, application):
        todo_id = application.create_todo("Orders")
        todo = application.get_todo(todo_id)
        assert todo.title == 'Orders'

    def test_add_items(self, application):
        todo_id = application.create_todo("Orders")
        application.add_item(todo_id, "Milk")
        application.add_item(todo_id, "Soap")
        application.add_item(todo_id, "Bread")
        todo = application.get_todo(todo_id)
        assert todo.collect_items() == [
            Item(title="Milk", status=ItemStatus.CREATED),
            Item(title="Soap", status=ItemStatus.CREATED),
            Item(title="Bread", status=ItemStatus.CREATED),
        ]

    def test_add_item_not_exists(self, application):
        with pytest.raises(AggregateNotFoundError):
            application.add_item(uuid.uuid4(), "Milk")

    def test_remove_item(self, application):
        todo_id = application.create_todo('Orders')
        item_id = application.add_item(todo_id, 'Milk')
        application.remove_item(todo_id, item_id)
        todo = application.get_todo(todo_id)
        assert todo.collect_items() == []

    def test_mark_done(self, application):
        todo_id = application.create_todo('Orders')
        item_id = application.add_item(todo_id, 'Milk')
        application.done_item(todo_id, item_id)
        todo = application.get_todo(todo_id)
        assert todo.collect_items() == [Item(title="Milk", status=ItemStatus.DONE)]