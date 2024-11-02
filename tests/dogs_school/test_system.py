from time import sleep
from uuid import uuid4

import pytest
from eventsourcing.system import (
    MultiThreadedRunner,
    System,
    SingleThreadedRunner,
)

from school.application import DogSchool
from school.domainmodel import DogAggregate
from school.service import DogService
from school.system import (
    Counters,
    Printers,
)


@pytest.fixture
def system():
    return System(
        pipes=[
            [DogSchool, Counters],
            [DogSchool, Printers],
            [Counters, Printers],
        ]
    )

@pytest.fixture
def multithread_persistence_runner(system):
    # Start running the system.
    # cipher_key = AESCipher.create_key(num_bytes=32)
    cipher_key = 'e+J7wVKCXB2+QTEdnbx6RMAHLNKZXhpF+f9lHEFVIio='
    runner = MultiThreadedRunner(
        system, env={
            'CIPHER_KEY': cipher_key,
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
def multithread_no_persistence_runner(system):
    runner = MultiThreadedRunner(system)
    runner.start()
    yield runner
    runner.stop()

@pytest.fixture
def single_thread_runner(system):
    runner = SingleThreadedRunner(system)
    runner.start()
    yield runner
    runner.stop()

def test_get_app_before_start():
    system = System(pipes=[[DogSchool]])
    runner = SingleThreadedRunner(system=system)
    school = runner.get(DogSchool)
    school.register_dog('Fluff')
    assert school.get_dog('Fluff')


def test_load(multithread_persistence_runner):
    runner = multithread_persistence_runner
    school = runner.get(DogSchool)
    for _ in range(1000):
        name = str(uuid4())
        school.register_dog(name)
        school.add_trick(name, str(uuid4()))

def test_with_service(single_thread_runner):
    runner = single_thread_runner
    school = runner.get(DogSchool)
    service = DogService(school, extra_dep=True)
    dog_id = service.create('Fluff')
    dog = service.get(dog_id)
    assert dog.name == 'Fluff'

def test_single_thread_runner(single_thread_runner):
    # Get the application objects.
    school = single_thread_runner.get(DogSchool)
    counters = single_thread_runner.get(Counters)

    # Generate some events.
    billy = 'Billy'
    milly = 'Milly'
    scrappy = 'Scrappy'

    school.register_dog(billy)
    school.register_dog(milly)
    school.register_dog(scrappy)

    school.add_trick(billy, 'roll over')
    school.add_trick(milly, 'roll over')
    school.add_trick(scrappy, 'roll over')

    # Check the results of processing the events.
    assert counters.get_count('Billy') == 1
    assert counters.get_count('Milly') == 1
    assert counters.get_count('Scrappy') == 1
    assert counters.get_count('roll over') == 3
    assert counters.get_count('fetch ball') == 0
    assert counters.get_count('play dead') == 0

    # Generate more events.
    school.add_trick(billy, 'fetch ball')
    school.add_trick(milly, 'fetch ball')

    # Check the results.
    assert counters.get_count('roll over') == 3
    assert counters.get_count('fetch ball') == 2
    assert counters.get_count('play dead') == 0

    # Generate more events.
    school.add_trick(billy, 'play dead')

    # Check the results.
    assert counters.get_count('roll over') == 3
    assert counters.get_count('fetch ball') == 2
    assert counters.get_count('play dead') == 1

    snapshots = school.get_snapshot(DogAggregate.create_id(billy))
    assert snapshots

    billy = school.get_dog(billy)
    assert billy

def test_multi_thread_runner(single_thread_runner):
    # Get the application objects.
    school = single_thread_runner.get(DogSchool)
    counters = single_thread_runner.get(Counters)

    # Generate some events.
    billy = 'Billy'
    milly = 'Milly'
    scrappy = 'Scrappy'

    school.register_dog(billy)
    school.register_dog(milly)
    school.register_dog(scrappy)

    school.add_trick(billy, 'roll over')
    school.add_trick(milly, 'roll over')
    school.add_trick(scrappy, 'roll over')

    sleep(0.1)
    # Check the results of processing the events.
    assert counters.get_count('Billy') == 1
    assert counters.get_count('Milly') == 1
    assert counters.get_count('Scrappy') == 1
    assert counters.get_count('roll over') == 3
    assert counters.get_count('fetch ball') == 0
    assert counters.get_count('play dead') == 0

    # Generate more events.
    school.add_trick(billy, 'fetch ball')
    school.add_trick(milly, 'fetch ball')

    sleep(0.1)
    # Check the results.
    assert counters.get_count('roll over') == 3
    assert counters.get_count('fetch ball') == 2
    assert counters.get_count('play dead') == 0

    # Generate more events.
    school.add_trick(billy, 'play dead')

    # Check the results.
    sleep(0.1)
    assert counters.get_count('roll over') == 3
    assert counters.get_count('fetch ball') == 2
    assert counters.get_count('play dead') == 1

    snapshots = school.get_snapshot(DogAggregate.create_id(billy))
    assert snapshots

    billy = school.get_dog(billy)
    assert billy

def test_persistence_multithread_runner(multithread_persistence_runner):
    # Get the application objects.
    school = multithread_persistence_runner.get(DogSchool)

    # Generate some events.
    billy = 'Billy'
    milly = 'Milly'
    scrappy = 'Scrappy'

    school.register_dog(billy)
    school.register_dog(milly)
    school.register_dog(scrappy)

    school.add_trick(billy, 'roll over')
    school.add_trick(milly, 'roll over')
    school.add_trick(scrappy, 'roll over')

    # Generate more events.
    school.add_trick(billy, 'fetch ball')
    school.add_trick(milly, 'fetch ball')

    # Generate more events.
    school.add_trick(billy, 'play dead')

    billy = school.get_dog(billy)
    assert billy
