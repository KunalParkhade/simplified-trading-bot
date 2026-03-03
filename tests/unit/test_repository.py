"""Unit tests for OrderRepository using a real in-memory SQLite database.

These tests verify SQL behaviour — they deliberately avoid mocking the DB
layer so that any ORM query regressions are caught immediately.
"""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, build_session_factory
from app.db.models import Order
from app.db.repository import OrderRepository
from app.schemas.order import OrderResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

IN_MEMORY_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Create isolated in-memory SQLite engine + tables for each test."""
    engine = create_async_engine(
        IN_MEMORY_URL,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = build_session_factory(engine)
    async with factory() as sess:
        yield sess

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _make_order_response(**overrides) -> OrderResponse:
    """Build an ``OrderResponse`` with sensible defaults."""
    defaults = {
        "order_id": 100001,
        "symbol": "BTCUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "status": "FILLED",
        "executed_qty": 0.001,
        "avg_price": 50000.0,
        "stop_price": 0.0,
        "timestamp": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return OrderResponse(**defaults)


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------


class TestCreate:
    async def test_create_returns_order_orm_instance(self, session: AsyncSession):
        repo = OrderRepository(session)
        result = await repo.create(_make_order_response())
        assert isinstance(result, Order)

    async def test_create_persists_order_id(self, session: AsyncSession):
        repo = OrderRepository(session)
        result = await repo.create(_make_order_response(order_id=999))
        assert result.order_id == 999

    async def test_create_persists_symbol(self, session: AsyncSession):
        repo = OrderRepository(session)
        result = await repo.create(_make_order_response(symbol="ETHUSDT"))
        assert result.symbol == "ETHUSDT"

    async def test_create_persists_all_fields(self, session: AsyncSession):
        repo = OrderRepository(session)
        ts = datetime(2024, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
        obj = _make_order_response(
            order_id=200,
            symbol="ETHUSDT",
            side="SELL",
            order_type="LIMIT",
            status="NEW",
            executed_qty=1.5,
            avg_price=3500.0,
            stop_price=0.0,
            timestamp=ts,
        )
        result = await repo.create(obj)
        assert result.side == "SELL"
        assert result.order_type == "LIMIT"
        assert result.status == "NEW"
        assert result.executed_qty == 1.5
        assert result.avg_price == 3500.0

    async def test_create_assigns_db_primary_key(self, session: AsyncSession):
        repo = OrderRepository(session)
        result = await repo.create(_make_order_response())
        assert result.id is not None
        assert result.id >= 1

    async def test_create_multiple_orders_get_distinct_pks(self, session: AsyncSession):
        repo = OrderRepository(session)
        a = await repo.create(_make_order_response(order_id=1))
        b = await repo.create(_make_order_response(order_id=2))
        assert a.id != b.id


# ---------------------------------------------------------------------------
# get_by_id()
# ---------------------------------------------------------------------------


class TestGetById:
    async def test_get_by_id_returns_created_order(self, session: AsyncSession):
        repo = OrderRepository(session)
        created = await repo.create(_make_order_response())
        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_by_id_returns_none_for_missing(self, session: AsyncSession):
        repo = OrderRepository(session)
        result = await repo.get_by_id(99999)
        assert result is None


# ---------------------------------------------------------------------------
# get_by_order_id()
# ---------------------------------------------------------------------------


class TestGetByOrderId:
    async def test_get_by_order_id_finds_created_order(self, session: AsyncSession):
        repo = OrderRepository(session)
        await repo.create(_make_order_response(order_id=555))
        result = await repo.get_by_order_id(555)
        assert result is not None
        assert result.order_id == 555

    async def test_get_by_order_id_returns_none_for_missing(self, session: AsyncSession):
        repo = OrderRepository(session)
        result = await repo.get_by_order_id(99999)
        assert result is None


# ---------------------------------------------------------------------------
# list_by_symbol()
# ---------------------------------------------------------------------------


class TestListBySymbol:
    async def test_list_by_symbol_returns_only_matching_symbol(self, session: AsyncSession):
        repo = OrderRepository(session)
        await repo.create(_make_order_response(order_id=1, symbol="BTCUSDT"))
        await repo.create(_make_order_response(order_id=2, symbol="ETHUSDT"))
        await repo.create(_make_order_response(order_id=3, symbol="BTCUSDT"))

        results = await repo.list_by_symbol("BTCUSDT")
        assert all(r.symbol == "BTCUSDT" for r in results)
        assert len(results) == 2

    async def test_list_by_symbol_returns_empty_for_unknown_symbol(self, session: AsyncSession):
        repo = OrderRepository(session)
        await repo.create(_make_order_response(order_id=1, symbol="BTCUSDT"))
        results = await repo.list_by_symbol("XYZUSDT")
        assert results == []

    async def test_list_by_symbol_respects_limit(self, session: AsyncSession):
        repo = OrderRepository(session)
        for i in range(5):
            await repo.create(_make_order_response(order_id=i + 1, symbol="BTCUSDT"))
        results = await repo.list_by_symbol("BTCUSDT", limit=3)
        assert len(results) == 3

    async def test_list_by_symbol_respects_offset(self, session: AsyncSession):
        repo = OrderRepository(session)
        for i in range(4):
            await repo.create(_make_order_response(order_id=i + 1, symbol="BTCUSDT"))
        results = await repo.list_by_symbol("BTCUSDT", limit=10, offset=2)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# list_all()
# ---------------------------------------------------------------------------


class TestListAll:
    async def test_list_all_returns_all_orders(self, session: AsyncSession):
        repo = OrderRepository(session)
        await repo.create(_make_order_response(order_id=1, symbol="BTCUSDT"))
        await repo.create(_make_order_response(order_id=2, symbol="ETHUSDT"))
        await repo.create(_make_order_response(order_id=3, symbol="SOLUSDT"))

        results = await repo.list_all()
        assert len(results) == 3

    async def test_list_all_respects_limit(self, session: AsyncSession):
        repo = OrderRepository(session)
        for i in range(6):
            await repo.create(_make_order_response(order_id=i + 1))
        results = await repo.list_all(limit=4)
        assert len(results) == 4

    async def test_list_all_respects_offset(self, session: AsyncSession):
        repo = OrderRepository(session)
        for i in range(5):
            await repo.create(_make_order_response(order_id=i + 1))
        results = await repo.list_all(limit=100, offset=3)
        assert len(results) == 2

    async def test_list_all_returns_empty_when_no_orders(self, session: AsyncSession):
        repo = OrderRepository(session)
        results = await repo.list_all()
        assert results == []
