# -*- coding: utf-8 -*-
import abc
from abc import ABC
from typing import (
    Any,
    Dict,
    cast,
)
from uuid import UUID

from eventsourcing.application import (
    Application,
    AggregateNotFoundError,
)

from .domainmodel import DogAggregate

class IDogSchool(ABC):
    @abc.abstractmethod
    def register_dog(self, name: str) -> UUID:
        ...

    @abc.abstractmethod
    def add_trick(self, dog_name: str, trick: str) -> None:
        ...

    @abc.abstractmethod
    def get_dog(self, dog_name: str) -> Dict[str, Any]:
        ...

class DogSchool(IDogSchool, Application):
    is_snapshotting_enabled = True
    snapshotting_intervals = {DogAggregate: 100}

    def register_dog(self, name: str) -> UUID:
        try:
            dog = self.repository.get(DogAggregate.create_id(name))
        except AggregateNotFoundError:
            dog = DogAggregate(name)
            self.save(dog)
        return dog.id

    def add_trick(self, dog_name: str, trick: str) -> None:
        dog_id = DogAggregate.create_id(dog_name)
        dog = cast(DogAggregate, self.repository.get(dog_id))
        dog.add_trick(trick)
        self.save(dog)

    def get_dog(self, dog_name: str) -> Dict[str, Any]:
        dog_id = DogAggregate.create_id(dog_name)
        dog = self.repository.get(dog_id)
        return {"name": dog.name, "tricks": dog.tricks}

    def get_snapshot(self, dog_id: UUID):
        return self.snapshots.get(dog_id)
