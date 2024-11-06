import abc
from uuid import UUID

from d3m.domain import DomainCommand
from d3m.hc import HandlersCollection
from d3m.uow import (
    UnitOfWorkBuilder,
    IRepository,
)

from group.model import Group

collection = HandlersCollection()


class BaseCommand(DomainCommand, domain='group'):
    pass


class CreateGroupCommand(BaseCommand):
    name: str


class ProduceGroupCommand(BaseCommand):
    reference: UUID


class IGroupRepository(IRepository, abc.ABC):
    @abc.abstractmethod
    def create(self, name: str) -> Group:
        ...

    @abc.abstractmethod
    async def get(self, reference: UUID) -> Group:
        ...


@collection.register
async def create_group(
        cmd: CreateGroupCommand,
        uow_builder: UnitOfWorkBuilder[IGroupRepository],
):
    async with uow_builder() as uow:
        group = uow.repository.create(name=cmd.name)
        await uow.apply()
    return group.__reference__


@collection.register
async def produce_group(
        cmd: ProduceGroupCommand,
        uow_builder: UnitOfWorkBuilder[IGroupRepository],
):
    async with uow_builder() as uow:
        group = await uow.repository.get(cmd.reference)
    return group
