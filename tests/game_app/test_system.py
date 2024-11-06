import pytest
from eventsourcing.system import (
    System,
    SingleThreadedRunner,
    MultiThreadedRunner,
)
from sqlalchemy import create_engine

from game.application import Game
from game.system import (
    HallOfFame,
    HallOfFameMaterialize,
)


@pytest.fixture
def system():
    return System(
        pipes=[
            [Game, HallOfFame],
            [HallOfFame, HallOfFameMaterialize],
        ]
    )


@pytest.fixture
def single_threaded_runner(system, ):
    datastore = create_engine("postgresql+psycopg://root:root@localhost:55000/eventsourcing")

    runner = SingleThreadedRunner(
        system, env={
            'PERSISTENCE_MODULE': "eventsourcing.postgres",
            'POSTGRES_DBNAME': 'eventsourcing',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '55000',
            'POSTGRES_USER': 'root',
            'POSTGRES_PASSWORD': 'root',
            'postgresql_engine': datastore  # extra dep example,
        }
    )
    runner.start()
    yield runner
    runner.stop()


@pytest.fixture
def multi_thread_persistence_runner(system):
    datastore = create_engine("postgresql+psycopg://root:root@localhost:55000/eventsourcing")
    runner = MultiThreadedRunner(
        system, env={
            'PERSISTENCE_MODULE': "eventsourcing.postgres",
            'POSTGRES_DBNAME': 'eventsourcing',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '55000',
            'POSTGRES_USER': 'root',
            'POSTGRES_PASSWORD': 'root',
            'postgresql_engine': datastore  # extra dep example,
        }
        )
    runner.start()
    yield runner
    runner.stop()


def test_system(multi_thread_persistence_runner):
    game = multi_thread_persistence_runner.get(Game)
    john = game.register("John")
    alice = game.register("Alice")
    kate = game.register("Kate")
    lui = game.register("Lui")

    game.add_score(alice, 20)
    game.add_score(kate, 15)
    game.add_score(john, 10)
    game.add_score(lui, 5)

    score_table = multi_thread_persistence_runner.get(HallOfFame)
    assert score_table.get_top() == [('Alice', 20), ('Kate', 15), ('John', 10)]

    game.add_score(lui, 30)
    assert score_table.get_top() == [('Lui', 35), ('Alice', 20), ('Kate', 15)]