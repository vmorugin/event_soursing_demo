from __future__ import annotations

import datetime as dt
import typing as t
from uuid import UUID

from eventsourcing.utils import get_topic
from pydantic import BaseModel


class DomainEvent(BaseModel):
    originator_id: UUID
    originator_version: int
    timestamp: dt.datetime

    class Config:
        frozen = True


class TodoDomainEvent(DomainEvent):
    pass


class Aggregate(BaseModel):
    id: UUID
    version: int
    created_on: dt.datetime
    modified_on: dt.datetime

    def __eq__(self, other):
        return isinstance(other, Aggregate) and self.id == other.id

    class Config:
        frozen = True


class Snapshot(BaseModel):
    topic: str
    state: dict[str, t.Any]
    originator_id: UUID
    originator_version: int
    timestamp: dt.datetime

    @classmethod
    def take(cls, aggregate: Aggregate) -> Snapshot:
        return Snapshot(
            originator_id=aggregate.id,
            originator_version=aggregate.version,
            timestamp=create_timestamp(),
            topic=get_topic(type(aggregate)),
            state=aggregate.model_dump(),
        )


def create_timestamp() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)
