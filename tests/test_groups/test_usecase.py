from uuid import UUID

import pytest
from black.trans import defaultdict
from d3m.core import get_messagebus
from d3m.domain import get_event_class
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
from group.usecase import (
    IGroupRepository,
    collection,
    CreateGroupCommand,
    ProduceGroupCommand,
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
        for db_event in events:
            event_cls = get_event_class(db_event['domain'], db_event['name'])
            event = event_cls.load(
                    payload=db_event['payload'],
                    reference=db_event['reference'],
                    timestamp=db_event['timestamp']
                )
            aggregate = mutate(event, aggregate)
            return aggregate

    async def commit(self) -> None:
        while self._seen:
            reference, aggregate = self._seen.popitem()
            for event in aggregate.collect_events():
                self._engine[reference].append(
                    dict(
                        reference=event.__reference__,
                        timestamp=event.__timestamp__,
                        domain=event.__domain_name__,
                        name=event.__class__.__name__,
                        payload=event.model_dump(mode='json'),
                    )
                )


class TestUsecase:
    @pytest.fixture
    def fake_engine(self):
        return defaultdict(list[dict])

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
        await mb.close()

    @pytest.fixture
    def setup(self, messagebus):
        self._messagebus = messagebus

    async def test_create(self, setup):
        command = CreateGroupCommand(name='test')
        result = await self._messagebus.handle_message(command)
        assert isinstance(result, UUID)

    async def test_create_and_get(self, setup):
        result = await self._messagebus.handle_message(CreateGroupCommand(name='test'))
        aggregate = await self._messagebus.handle_message(ProduceGroupCommand(reference=result))
        assert isinstance(aggregate, Group)
        assert aggregate.__version__ == 1
        assert aggregate.state.name == 'test'
        assert aggregate.state.members == {}
        assert aggregate.state.parent_id is None
