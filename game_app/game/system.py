from functools import singledispatchmethod

import sqlalchemy as sa
from uuid import (
    UUID,
    uuid5,
    NAMESPACE_URL,
)

from eventsourcing.application import (
    ProcessingEvent,
    AggregateNotFoundError,
)
from eventsourcing.domain import (
    DomainEventProtocol,
    Aggregate,
    event,
)
from eventsourcing.system import (
    ProcessApplication,
    Follower,
)
from sqlalchemy import Engine

from game.domainmodel import Player


class HighScoreTable(Aggregate):
    def __init__(self):
        self.scores: dict[str, tuple[str, int]] = {}

    @classmethod
    def create_id(cls) -> UUID:
        return uuid5(NAMESPACE_URL, '/high_score_table')

    @event('PlayerRegistered')
    def register(self, player_id: UUID, name: str):
        self.scores[str(player_id)] = (name, 0)

    @event("HighScoreTableUpdated")
    def increment_score(self, player_id: UUID, score: int):
        self.scores[str(player_id)] = self.scores[str(player_id)][0], self.scores[str(player_id)][1] + score

    def get_top(self):
        return sorted(self.scores.values(), key=lambda x: x[1], reverse=True)


class HallOfFame(ProcessApplication):
    is_snapshotting_enabled = True
    snapshotting_intervals = {HighScoreTable: 100, Player: 100}

    @singledispatchmethod
    def policy(self, domain_event: DomainEventProtocol, processing_event: ProcessingEvent) -> None:
        ...

    @policy.register
    def _(self, domain_event: Player.Registered, processing_event: ProcessingEvent) -> None:
        try:
            table = self.repository.get(HighScoreTable.create_id())
        except AggregateNotFoundError:
            table = HighScoreTable()
        table.register(player_id=domain_event.originator_id, name=domain_event.name)
        processing_event.collect_events(table)

    @policy.register
    def _(self, domain_event: Player.AddedScore, processing_event: ProcessingEvent) -> None:
        score = domain_event.points
        player_id = domain_event.originator_id
        try:
            table = self.repository.get(HighScoreTable.create_id())
        except AggregateNotFoundError:
            table = HighScoreTable()
        table.increment_score(player_id, score)
        processing_event.collect_events(table)

    def get_top(self):
        try:
            table = self.repository.get(HighScoreTable.create_id())
        except AggregateNotFoundError:
            return []
        return table.get_top()


class HallOfFameMaterialize(Follower):

    def __init__(self, env: dict):
        self.engine: Engine = env['postgresql_engine']  # todo: should be smth like a dishka container
        super().__init__(env)

    @singledispatchmethod
    def policy(self, domain_event: DomainEventProtocol, processing_event: ProcessingEvent) -> None:
        """
        For example
        Here you can publish domain event to RMQ, parse in external service and record the replica-view database.
        """

    @policy.register
    def _(self, domain_event: HighScoreTable.PlayerRegistered, processing_event: ProcessingEvent) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO 
                    high_score (name, player_id, score) 
                    VALUES (:name, :player_id, 0)
                    ON CONFLICT (player_id) DO UPDATE
                    SET name = :name 
                    """
                ), {'name': domain_event.name, 'player_id': domain_event.player_id}
            )
        processing_event.collect_events(domain_event)

    @policy.register
    def _(self, domain_event: HighScoreTable.HighScoreTableUpdated, processing_event: ProcessingEvent) -> None:
        """
        Re-create a state of an aggregate and write denormalized view
        Example bellow
        """
        with self.engine.begin() as conn:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO 
                    high_score (score, name, player_id) 
                    VALUES (:score, :name, :player_id)
                    ON CONFLICT (player_id) DO UPDATE
                    SET score = high_score.score + :score 
                    """
                ), {'score': domain_event.score, 'player_id': domain_event.player_id, 'name': None}
            )
