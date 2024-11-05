from uuid import UUID

from eventsourcing.application import Application
from eventsourcing.persistence import IntegrityError

from game.domainmodel import Player


class Game(Application):
    snapshotting_intervals = {Player: 10}
    is_snapshotting_enabled = True

    def register(self, name: str):
        player = Player(name)
        try:
            self.save(player)
        except IntegrityError:
            player = self.repository.get(Player.create_id(name))
        return player.id

    def get(self, player_id: UUID) -> Player:
        return self.repository.get(player_id)

    def add_score(self, player_id: UUID, score: int):
        player = self.repository.get(player_id)
        player.add_score(score)
        self.save(player)
