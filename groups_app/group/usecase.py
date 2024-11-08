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


class IGroupRepository(IRepository, abc.ABC):
    @abc.abstractmethod
    def create(self, name: str, parent_id: UUID | None) -> Group:
        ...

    @abc.abstractmethod
    async def get(self, reference: UUID) -> Group:
        ...


class BaseCommand(DomainCommand, domain='group'):
    pass


class CreateGroupCommand(BaseCommand):
    parent_id: UUID | None = None
    name: str



@collection.register
async def create_group(
        cmd: CreateGroupCommand,
        uow_builder: UnitOfWorkBuilder[IGroupRepository],
):
    async with uow_builder() as uow:
        group = uow.repository.create(name=cmd.name, parent_id=cmd.parent_id)
        if cmd.parent_id:
            parent = await uow.repository.get(cmd.parent_id)
            parent.add_member(group.state.name, group.__reference__)
        await uow.apply()
    return group.__reference__


class RenameGroupCommand(BaseCommand):
    name: str
    reference: UUID


@collection.register
async def rename_group(
        cmd: RenameGroupCommand,
        uow_builder: UnitOfWorkBuilder[IGroupRepository],
):
    async with uow_builder() as uow:
        group = await uow.repository.get(reference=cmd.reference)
        group.rename(cmd.name)
        await uow.apply()


class ProduceGroupCommand(BaseCommand):
    reference: UUID


@collection.register
async def produce_group(
        cmd: ProduceGroupCommand,
        uow_builder: UnitOfWorkBuilder[IGroupRepository],
):
    async with uow_builder() as uow:
        group = await uow.repository.get(cmd.reference)
    return group
