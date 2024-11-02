# -*- coding: utf-8 -*-
import uuid

from school.application import DogSchool


def test_dog_school() -> None:
    # Construct application object.
    app = DogSchool()

    # Call application command methods.
    app.register_dog("Fido")
    for i in range(20):
        app.add_trick("Fido", str(uuid.uuid4()))

    assert app.get_dog("Fido")

