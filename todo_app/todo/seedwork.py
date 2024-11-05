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

    @property
    def originator_id(self) -> UUID:
        return self.originator_id

    @property
    def originator_version(self) -> int:
        return self.originator_version

    class Config:
        frozen = True

class DomainCommand(BaseModel):
    class Config:
        frozen = True


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


TAggregate = t.TypeVar("TAggregate", bound=Aggregate)
MutatorFunction = t.Callable[..., t.Optional[TAggregate]]


def aggregate_projector(
        mutator: MutatorFunction[TAggregate],
) -> t.Callable[[TAggregate | None, t.Iterable[DomainEvent]], TAggregate | None]:
    def project_aggregate(
            aggregate: TAggregate | None, events: t.Iterable[DomainEvent]
    ) -> TAggregate | None:
        for event in events:
            aggregate = mutator(event, aggregate)
        return aggregate

    return project_aggregate
