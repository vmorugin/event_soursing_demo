import uuid
from uuid import NAMESPACE_URL

import pytest

from todo.domainmodel import (
    Todo,
    Created,
    Item,
    ItemStatus,
    mutate,
)
from todo.seedwork import Aggregate


class TestModel:
    @pytest.fixture
    def register_todo(self):
        def wrapper():
            return Todo.create(title='Goods')

        return wrapper

    @pytest.fixture
    def get_todo(self, register_todo):
        def wrapper():
            event = register_todo()
            return mutate(event, None)

        return wrapper

    @pytest.fixture
    def get_item(self):
        def wrapper(title: str = None, status: str = ItemStatus.CREATED):
            return Item(title=title or str(uuid.uuid4()), status=status)

        return wrapper

    @pytest.mark.parametrize('title, status, expected', (
            ('example', 'CREATED', uuid.UUID('39a9a60f-fee0-5c4c-9136-1e09ad417198')),
            ('EXAMPLE', 'CREATED', uuid.UUID('39a9a60f-fee0-5c4c-9136-1e09ad417198')),
            ('example', 'DONE', uuid.UUID('39a9a60f-fee0-5c4c-9136-1e09ad417198')),
            ('New todo', 'DONE', uuid.UUID('2bdb8cb9-e7e3-5c45-8301-d9f1c96b7512')),
    ))
    def test_item_id(self, get_item, title, status, expected):
        item = get_item(title=title, status=status)
        assert item.create_id() == expected

    @pytest.mark.parametrize('status', (
        'CREATED',
        'DONE',
    ))
    def test_item_valid_status(self, get_item, status):
        item = get_item(status=status)
        assert item.status == ItemStatus(status)

    def test_create(self):
        event = Todo.create('Goods')
        todo = mutate(event, None)
        assert isinstance(todo, Todo)
        assert isinstance(todo, Aggregate)
        assert todo.title == 'Goods'
        assert todo.collect_items() == []
        assert todo.id == uuid.uuid5(NAMESPACE_URL, '/todo/GOODS')
        assert isinstance(event, Created)

    def test_add_item(self, get_todo, get_item):
        todo = get_todo()
        item = get_item(title='NEW', status=ItemStatus.CREATED)
        item_added = todo.add_item(item.title)
        todo = mutate(item_added, todo)
        assert todo.collect_items() == [item]
        assert item_added.item.create_id() == uuid.UUID('61681e07-8010-5f7c-b5c8-cd2c880abdd2')

    def test_add_item_twice_no_event(self, get_todo, get_item):
        todo = get_todo()
        item = get_item(title='NEW', status=ItemStatus.CREATED)
        todo = mutate(todo.add_item(item.title), todo)
        todo = mutate(todo.add_item(item.title), todo)
        assert todo.collect_items() == [item]

    def test_remove_item(self, get_todo, get_item):
        todo = get_todo()
        item = get_item()
        item_added = todo.add_item(item.title)
        todo = mutate(item_added, todo)
        item_removed = todo.remove_item(item_added.item.create_id())
        todo = mutate(item_removed, todo)
        assert todo.collect_items() == []

    def test_remove_not_found(self, get_todo, get_item):
        item = get_item()
        todo = get_todo()
        event = todo.remove_item(item.create_id())
        todo = mutate(event, todo)
        assert todo.collect_items() == []

    def test_mark_done(self, get_todo, get_item):
        todo = get_todo()
        item = get_item(status=ItemStatus.DONE)
        todo = mutate(todo.add_item(item.title), todo)
        todo = mutate(todo.mark_done(item.create_id()), todo)
        assert todo.collect_items() == [item]
