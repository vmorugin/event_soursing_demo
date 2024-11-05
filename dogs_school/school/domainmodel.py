# -*- coding: utf-8 -*-
from __future__ import annotations
import uuid

from eventsourcing.domain import (
    Aggregate,
    event,
)


class DogAggregate(Aggregate):
    name: str
    tricks: list[str]

    @event("Registered")
    def __init__(self, name: str) -> None:
        self.name = name
        self.tricks = []

    @classmethod
    def create_id(cls, name: str) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_URL, f'/dogs/{name}')

    @event("TrickAdded")
    def add_trick(self, trick_name: str) -> None:
        self._check_too_many_tricks()
        self.tricks.append(trick_name)

    def _check_too_many_tricks(self):
        max_tricks = 20
        if len(self.tricks) >= max_tricks:
            raise ValueError(f"Not more then {max_tricks} tricks")
