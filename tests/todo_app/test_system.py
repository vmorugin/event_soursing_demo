from uuid import uuid4

import pytest
from eventsourcing.postgres import PostgresDatastore
from eventsourcing.system import (
    System,
    MultiThreadedRunner,
)
from eventsourcing.tests.postgres_utils import drop_postgres_table

from todo.application import TodoApp
from todo.domainmodel import Item


@pytest.fixture
def system():
    return System(pipes=[[TodoApp]])


@pytest.fixture
def multithread_persistence_compressed_runner(system):
    # Start running the system.
    # cipher_key = AESCipher.create_key(num_bytes=32)
    runner = MultiThreadedRunner(
        system, env={
            'CIPHER_KEY': 'e+J7wVKCXB2+QTEdnbx6RMAHLNKZXhpF+f9lHEFVIio=',
            'CIPHER_TOPIC': 'eventsourcing.cipher:AESCipher',
            'COMPRESSOR_TOPIC': 'eventsourcing.compressor:ZlibCompressor',
            'PERSISTENCE_MODULE': "eventsourcing.postgres",
            'POSTGRES_DBNAME': 'eventsourcing',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '55000',
            'POSTGRES_USER': 'root',
            'POSTGRES_PASSWORD': 'root',

        }
    )
    runner.start()
    yield runner
    runner.stop()


@pytest.fixture
def postgresql_datastore():
    yield PostgresDatastore(
        'eventsourcing',
        'localhost',
        '55000',
        'root',
        'root',
    )


@pytest.fixture
def clear_postgresql_datastore():
    datastore = PostgresDatastore(
        'eventsourcing',
        'localhost',
        '55000',
        'root',
        'root',
    )
    drop_postgres_table(datastore, 'todoapp_events')
    drop_postgres_table(datastore, 'todoapp_snapshots')
    yield datastore
    drop_postgres_table(datastore, 'todoapp_events')
    drop_postgres_table(datastore, 'todoapp_snapshots')


@pytest.fixture
def multithread_persistence_runner(system):
    # Start running the system.
    runner = MultiThreadedRunner(
        system, env={
            'PERSISTENCE_MODULE': "eventsourcing.postgres",
            'POSTGRES_DBNAME': 'eventsourcing',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '55000',
            'POSTGRES_USER': 'root',
            'POSTGRES_PASSWORD': 'root',

        }
    )
    runner.start()
    yield runner
    runner.stop()

@pytest.fixture
def multithread_persistence_runner_cleanup(clear_postgresql_datastore, multithread_persistence_runner):
    yield multithread_persistence_runner


@pytest.fixture
def multithread_no_persistence_runner(system):
    runner = MultiThreadedRunner(system)
    runner.start()
    yield runner
    runner.stop()


def test_without_storage(multithread_no_persistence_runner):
    app = multithread_no_persistence_runner.get(TodoApp)

    todo_id = app.create_todo('NewTodo')
    todo = app.get_todo(todo_id)
    assert todo.title == 'NewTodo'
    assert todo.collect_items() == []

    app.add_item(todo_id, "Bananas")
    sugar_id = app.add_item(todo_id, "Sugar")
    bread_id = app.add_item(todo_id, "Bread")
    todo = app.get_todo(todo_id)
    assert todo.collect_items() == [
        Item(title='Bananas', status='CREATED'),
        Item(title='Sugar', status='CREATED'),
        Item(title='Bread', status='CREATED'),
    ]

    assert app.add_item(todo_id, "Bread") == bread_id

    app.done_item(todo_id, sugar_id)
    app.remove_item(todo_id, bread_id)
    app.remove_item(todo_id, bread_id)
    todo = app.get_todo(todo_id)
    assert todo.collect_items() == [
        Item(title='Bananas', status='CREATED'),
        Item(title='Sugar', status='DONE'),
    ]


def test_with_pg(multithread_persistence_runner_cleanup):
    app = multithread_persistence_runner_cleanup.get(TodoApp)
    todo_id = app.create_todo('NewTodo')
    todo = app.get_todo(todo_id)
    assert todo.title == 'NewTodo'
    assert todo.collect_items() == []

    app.add_item(todo_id, "Bananas")
    sugar_id = app.add_item(todo_id, "Sugar")
    bread_id = app.add_item(todo_id, "Bread")
    todo = app.get_todo(todo_id)
    assert todo.collect_items() == [
        Item(title='Bananas', status='CREATED'),
        Item(title='Sugar', status='CREATED'),
        Item(title='Bread', status='CREATED'),
    ]

    assert app.add_item(todo_id, "Bread") == bread_id

    app.done_item(todo_id, sugar_id)
    app.remove_item(todo_id, bread_id)
    app.remove_item(todo_id, bread_id)
    todo = app.get_todo(todo_id)
    assert todo.collect_items() == [
        Item(title='Bananas', status='CREATED'),
        Item(title='Sugar', status='DONE'),
    ]


def test_with_pg_no_clear(multithread_persistence_runner):
    app = multithread_persistence_runner.get(TodoApp)
    todo_id = app.create_todo('NewTodo')
    app.add_item(todo_id, "Bananas")
    sugar_id = app.add_item(todo_id, "Sugar")
    bread_id = app.add_item(todo_id, "Bread")
    assert app.add_item(todo_id, "Bread") == bread_id
    app.done_item(todo_id, sugar_id)
    app.remove_item(todo_id, bread_id)
    app.remove_item(todo_id, bread_id)
    todo = app.get_todo(todo_id)
    assert todo.collect_items() == [
        Item(title='Bananas', status='CREATED'),
        Item(title='Sugar', status='DONE'),
    ]
