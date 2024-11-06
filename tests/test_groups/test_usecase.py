from uuid import UUID

import pytest
from d3m.core import get_messagebus
from d3m.uow import (
    UnitOfWorkBuilder,
    IRepository,
    IRepositoryBuilder,
    IUnitOfWorkCtxMgr,
)

from group.model import (
    Group,
    mutate,
)









class RepositoryBuilder(IRepositoryBuilder):

    def __init__(self, repository_class, engine):
        self._repository_class = repository_class
        self._engine = engine

    async def __call__(self, __uow_context_manager: IUnitOfWorkCtxMgr, /) -> IRepository:
        return self._repository_class(self._engine)


class FakeRepository(IGroupRepository):
    def __init__(self, engine: dict):
        self._engine = engine
        self._seen: dict[UUID, Group] = {}

    def create(self, name: str) -> Group:
        group = Group.create(name)
        self._seen[group.__reference__] = group
        return group

    async def get(self, reference: UUID) -> Group:
        events = self._engine.get(reference)
        aggregate = None
        for event in events:
            aggregate = mutate(event, aggregate)
        return aggregate


    async def commit(self) -> None:
        while self._seen:
            reference, aggregate = self._seen.popitem()
            for event in aggregate.collect_events():
                self._engine[reference] = dict(
                    reference=reference,
                    version=event.version,
                )





class TestUsecase:
    @pytest.fixture
    def fake_engine(self):
        return dict()

    @pytest.fixture
    async def messagebus(self, fake_engine):
        mb = get_messagebus()
        mb.include_collection(collection)
        uow_builder = UnitOfWorkBuilder(RepositoryBuilder(FakeRepository, fake_engine))
        mb.set_defaults(
            'group',
            uow_builder=uow_builder,
        )
        await mb.run()
        yield mb
        await mb.stop()

    @pytest.fixture
    def setup(self, messagebus):
        self._messagebus = messagebus

    async def test_create(self, setup):
        command = CreateGroupCommand(name='test')
        result = await self._messagebus.handle_message(command)
        assert isinstance(result, UUID)

    async def test_create_and_get(self, setup):
        result = await self._messagebus.handle_message(CreateGroupCommand(name='test'))
        await self._messagebus.handle_message(ProduceGroupCommand(reference=result))
