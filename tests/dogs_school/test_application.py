# -*- coding: utf-8 -*-
import uuid

from school.application import DogSchool


def test_dog_school() -> None:
    # Construct application object.
    app = DogSchool()

    # Call application command methods.
    app.register_dog("Fido")
    assert app.get_dog("Fido")

def test_add_trick():
    app = DogSchool()
    app.register_dog('Fido')
    tricks = [str(uuid.uuid4()) for _ in range(20)]
    for t in tricks:
        app.add_trick("Fido", t)
    fido = app.get_dog("Fido")
    assert fido['tricks'] == tricks

