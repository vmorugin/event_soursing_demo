from uuid import (
    uuid5,
    NAMESPACE_URL,
)

from game.domainmodel import Player


def test_init():
    player = Player("John")
    assert player.name == 'John'
    assert player.score == 0
    assert player.id == uuid5(NAMESPACE_URL, '/player/JOHN')


def test_update_score():
    player = Player("John")
    player.add_score(10)
    assert player.score == 10


def test_restore():
    player = Player("John")
    player.add_score(10)
    player.add_score(20)
    player.add_score(33)

    copy = None
    for e in player.collect_events():
        copy = e.mutate(copy)

    assert copy == player
