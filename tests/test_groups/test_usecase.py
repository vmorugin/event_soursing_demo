from uuid import (
    UUID,

)
import typing as t
import pytest
from black.trans import defaultdict
from d3m.core import get_messagebus
from d3m.domain import get_event_class
import sqlalchemy as sa
from d3m.uow import (
    UnitOfWorkBuilder,
    IRepository,
    IRepositoryBuilder,
    IUnitOfWorkCtxMgr,
)
from sqlalchemy import CursorResult
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    AsyncConnection,
)

from group.bases import DomainEvent
from group.model import (
    Group,
    GroupMember,
    GroupState,
)
from group.usecase import (
    IGroupRepository,
    collection,
    CreateGroupCommand,
    ProduceGroupCommand,
    RenameGroupCommand,
)


class RepositoryBuilder(IRepositoryBuilder):

    def __init__(self, repository_class, engine):
        self._repository_class = repository_class
        self._engine = engine

    async def __call__(self, __uow_context_manager: IUnitOfWorkCtxMgr, /) -> IRepository:
        return self._repository_class(self._engine)


class RealRepository(IGroupRepository):
    def __init__(self, engine: AsyncEngine):
        self._engine = engine
        self._seen: dict[UUID, Group] = {}

    def create(self, name: str, parent_id: UUID | None) -> Group:
        group = Group.create(name, parent_id=parent_id)
        self._seen[group.__reference__] = group
        return group

    async def get(self, reference: UUID) -> Group:
        snapshot = await self._get_snapshot(reference)
        return await self._get_events(snapshot, reference)

    async def _get_snapshot(self, reference: UUID) -> Group | None:
        async with self._engine.begin() as conn:
            cursor: CursorResult = await conn.execute(
                sa.text(
                    """
                    SELECT * FROM group_snapshots
                    WHERE originator_reference = :originator_reference 
                    ORDER BY originator_version DESC
                    LIMIT 1
                    """
                ), {'originator_reference': reference}
            )
            group_db = cursor.mappings().fetchone()
            if group_db:
                return Group(
                    __version__=group_db['originator_version'],
                    __reference__=group_db['originator_reference'],
                    state=GroupState.model_validate(group_db['state']),
                )

    async def _get_events(self, aggregate: Group | None, reference: UUID):
        async with self._engine.begin() as conn:
            cursor: CursorResult = await conn.execute(
                sa.text(
                    """
                    SELECT * FROM group_events
                    WHERE originator_reference = :originator_reference AND originator_version > :originator_version
                    ORDER BY originator_version ASC
                    """
                ), {'originator_reference': reference, 'originator_version': aggregate.__version__ if aggregate else 0}
            )
            events = cursor.mappings().fetchall()
        for db_event in events:
            event_cls = get_event_class(db_event['domain'], db_event['name'])
            event = t.cast(
                DomainEvent, event_cls.load(
                    payload=dict(
                        originator_version=db_event['originator_version'],
                        originator_reference=db_event['originator_reference'],
                        **db_event['payload'],
                    ),
                    reference=db_event['event_reference'],
                    timestamp=db_event['timestamp']
                )
            )
            aggregate = event.mutate(aggregate)
        group = t.cast(Group, aggregate)
        self._seen[group.__reference__] = group
        return group

    async def commit(self) -> None:
        async with self._engine.begin() as conn:
            while self._seen:
                reference, aggregate = self._seen.popitem()
                for event in aggregate.collect_events():
                    if event.originator_version % 100 == 0:
                        await self._save_snapshot(aggregate, conn)
                    await self._save_event(event, conn)
            await conn.commit()

    async def _save_snapshot(self, aggregate: Group, conn: AsyncConnection):
        await conn.execute(
            sa.text(
                """
                    INSERT INTO group_snapshots (originator_reference, domain, name, state, originator_version)
                    VALUES (:originator_reference, :domain, :name, :state, :originator_version)
                """
            ), dict(
                originator_reference=aggregate.__reference__,
                originator_version=aggregate.__version__,
                domain=aggregate.__domain_name__,
                name=aggregate.__class__.__name__,
                state=aggregate.state.model_dump_json(),
            )
        )

    async def _save_event(self, event: DomainEvent, conn: AsyncConnection):
        await conn.execute(
            sa.text(
                """
                    INSERT INTO group_events (originator_reference, timestamp, domain, name, payload, originator_version, event_reference)
                    VALUES (:originator_reference, :timestamp, :domain, :name, :payload, :originator_version, :event_reference)
                """
            ), dict(
                originator_reference=event.originator_reference,
                originator_version=event.originator_version,
                event_reference=event.__reference__,
                timestamp=event.__timestamp__,
                domain=event.__domain_name__,
                name=event.__class__.__name__,
                payload=event.model_dump_json(),
            )
        )


class FakeRepository(IGroupRepository):
    def __init__(self, engine: dict):
        self._event_store = engine
        self._seen: dict[UUID, Group] = {}

    def create(self, name: str, parent_id: UUID | None) -> Group:
        group = Group.create(name, parent_id=parent_id)
        self._seen[group.__reference__] = group
        return group

    async def get(self, reference: UUID) -> Group:
        events = self._event_store.get(reference)
        aggregate = None  # todo: get from snapshot
        for db_event in events:
            event_cls = get_event_class(db_event['domain'], db_event['name'])
            event = t.cast(
                DomainEvent, event_cls.load(
                    payload=dict(
                        originator_version=db_event['originator_version'],
                        originator_reference=db_event['originator_reference'],
                        **db_event['payload'],
                    ),
                    reference=db_event['event_reference'],
                    timestamp=db_event['timestamp']
                )
            )
            aggregate = event.mutate(aggregate)
        group = t.cast(Group, aggregate)
        self._seen[group.__reference__] = group
        return group

    async def commit(self) -> None:
        while self._seen:
            reference, aggregate = self._seen.popitem()
            for event in aggregate.collect_events():
                self._event_store[reference].append(
                    dict(
                        originator_reference=event.originator_reference,
                        originator_version=event.originator_version,
                        event_reference=event.__reference__,
                        timestamp=event.__timestamp__,
                        domain=event.__domain_name__,
                        name=event.__class__.__name__,
                        payload=event.model_dump(),
                    )
                )


class TestUsecase:
    @pytest.fixture
    def fake_engine(self):
        return defaultdict(list[dict])

    @pytest.fixture
    def real_engine(self):
        return create_async_engine('postgresql+psycopg://root:root@localhost:55000/eventsourcing')

    @pytest.fixture
    async def messagebus(self, fake_engine, real_engine):
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

    async def test_create_root(self, setup):
        command = CreateGroupCommand(name='test')
        result = await self._messagebus.handle_message(command)
        assert isinstance(result, UUID)

    async def test_create_root_and_get(self, setup):
        root_id = await self._messagebus.handle_message(CreateGroupCommand(name='test'))
        aggregate = await self._messagebus.handle_message(ProduceGroupCommand(reference=root_id))
        assert isinstance(aggregate, Group)
        assert aggregate.__version__ == 1
        assert aggregate.state.name == 'test'
        assert aggregate.state.members == {}
        assert aggregate.state.parent_id is None

    async def test_rename(self, setup):
        group_id = await self._messagebus.handle_message(CreateGroupCommand(name='test'))
        await self._messagebus.handle_message(RenameGroupCommand(reference=group_id, name='new'))
        aggregate = await self._messagebus.handle_message(ProduceGroupCommand(reference=group_id))
        assert isinstance(aggregate, Group)
        assert aggregate.__version__ == 2
        assert aggregate.state.name == 'new'

    async def test_create_with_parent(self, setup):
        parent_id = await self._messagebus.handle_message(CreateGroupCommand(name='test'))
        member_id = await self._messagebus.handle_message(CreateGroupCommand(name='member', parent_id=parent_id))
        parent = await self._messagebus.handle_message(ProduceGroupCommand(reference=parent_id))
        member = await self._messagebus.handle_message(ProduceGroupCommand(reference=member_id))

        assert isinstance(parent, Group)
        assert parent.__version__ == 2
        assert parent.state.members == {member_id: GroupMember(reference=member.__reference__, name=member.state.name)}
        assert parent.state.parent_id is None

        assert isinstance(member, Group)
        assert member.__version__ == 1
        assert member.state.members == {}
        assert member.state.parent_id == parent_id
