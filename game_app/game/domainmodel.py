from uuid import (
    UUID,
    uuid5,
    NAMESPACE_URL,
)

from eventsourcing.domain import (
    Aggregate,
    event,
)


class Player(Aggregate):
    @event("Registered")
    def __init__(self, name: str):
        self.name = name
        self.score = 0

    @event("AddedScore")
    def add_score(self, points: int):
        self.score += points

    @classmethod
    def create_id(cls, name: str) -> UUID:
        return uuid5(NAMESPACE_URL, f'/player/{name.upper()}')
