from uuid import UUID

import pytest

from school.domainmodel import (
    DogAggregate,
    Registered,
    Trick,
)


class TestModel:
    def test_init(self):
        dog = DogAggregate("Fluff")
        assert isinstance(dog, DogAggregate)
        assert isinstance(dog.id, UUID)

    def test_register(self):
        dog = DogAggregate.register('Fluff')
        events = list(dog.collect_events())
        assert len(events) == 1
        event = events.pop()
        assert isinstance(event, Registered)
        assert event.name == 'Fluff'

    def test_add_item(self):
        dog = DogAggregate('Fluff')
        dog.add_trick('jump')
        assert dog.tricks == (Trick('jump'),)

    def test_mutate(self):
        dog = DogAggregate.register('Fluff')
        dog.add_trick('jump')
        copy = None
        for event in dog.collect_events():
            copy = event.mutate(copy)

        assert copy == dog

    def test_immutable_name(self):
        dog = DogAggregate.register('Fluff')
        with pytest.raises(AttributeError):
            dog.name = 'Buff'
        assert dog.name == 'Fluff'

    def test_immutable_tricks(self):
        dog = DogAggregate.register('Fluff')
        dog.add_trick('trick')
        assert dog.tricks == (Trick(name='trick'),)
        with pytest.raises(AttributeError):
            dog.tricks = ()

    def test_create_id(self):
        dog = DogAggregate.create_id('Name')
        assert dog == UUID('aacca0d3-e26b-5a67-b46c-17e7ae04abf9')
