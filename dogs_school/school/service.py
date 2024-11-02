from uuid import UUID

from eventsourcing.application import Application

from school.application import IDogSchool


class DogService:
    def __init__(
            self,
            dog_school: IDogSchool | Application,
            extra_dep: bool,
    ):
        self._dog_school = dog_school
        self._extra_dep = extra_dep

    def create(self, dog_name: str):
        assert self._extra_dep  # example: redlock or adapter
        dog_id = self._dog_school.register_dog(dog_name)
        return dog_id

    def get(self, dog_id: UUID):
        assert self._extra_dep  # example: redlock or adapter
        return self._dog_school.repository.get(dog_id)
