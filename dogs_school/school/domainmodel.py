# -*- coding: utf-8 -*-
from __future__ import annotations
import typing as t
import uuid

from dataclasses import dataclass
from eventsourcing.domain import (
    Aggregate,
)

@dataclass
class Trick:
    name: str


class DogAggregate(Aggregate):
    _name: str
    _tricks: list[Trick]

    class_version = 2

    @classmethod
    def register(cls, name: str) -> t.Self:
        dog = cls._create(Registered, id=cls.create_id(name), name=name)
        return dog

    def __init__(self, name: str) -> None:
        self._name = name
        self._tricks = []

    @property
    def name(self):
        return self._name

    @property
    def tricks(self):
        return tuple(self._tricks)

    @classmethod
    def create_id(cls, name: str) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_URL, f'/dogs/{name}')

    def add_trick(self, trick_name: str) -> None:
        self._check_too_many_tricks()
        trick = Trick(name=trick_name)
        self.trigger_event(TrickAdded, name=trick.name)

    def _check_too_many_tricks(self):
        max_tricks = 20000000
        if len(self._tricks) >= max_tricks:
            raise ValueError(f"Not more then {max_tricks} tricks")

    @staticmethod
    def upcast_v1_v2(state):
        state["_tricks"] = [Trick(name=trick) for trick in state['_tricks']]


class TrickAdded(DogAggregate.Event):
    name: str

    def apply(self, aggregate: DogAggregate) -> None:
        aggregate._tricks = [*aggregate.tricks, Trick(name=self.name)]

    @staticmethod
    def upcast_v1_v2(state):
        state["name"] = Trick(name=state['trick_name'])


class Registered(DogAggregate.Created):
    name: str

    def apply(self, aggregate: DogAggregate) -> None:
        aggregate._name = self.name