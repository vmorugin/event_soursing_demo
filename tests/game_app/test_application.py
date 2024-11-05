import pytest

from game.application import Game


@pytest.fixture
def app():
    return Game()

def test_register(app):
    john_id = app.register("John")
    john = app.get(john_id)
    assert john.name == 'John'

def test_add_score(app):
    john_id = app.register("John")
    app.add_score(john_id, 10)
    app.add_score(john_id, 20)
    john = app.get(john_id)
    assert john.score == 30
