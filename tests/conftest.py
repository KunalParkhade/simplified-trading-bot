"""Shared pytest fixtures for the trading-bot test suite.

Strategy
--------
- Unit tests use direct imports and ``respx`` / ``AsyncMock`` for mocking.
- Integration tests drive the FastAPI app via ``httpx.ASGITransport`` — no
  real network calls and no real Binance API.
- ``get_binance_client`` is overridden with an ``AsyncMock``.
- ``get_db_session`` is overridden with an ``AsyncMock`` whose ``add`` and
  ``commit`` methods are no-ops, keeping integration tests free of a real DB.
- Repository unit tests (``tests/unit/test_repository.py``) build their own
  in-memory SQLite engine so they test real SQL behaviour.
"""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_binance_client, get_db_session
from app.main import create_app

# ---------------------------------------------------------------------------
# Reusable Binance raw response payloads
# ---------------------------------------------------------------------------

MARKET_ORDER_RAW = {
    "orderId": 100001,
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "status": "FILLED",
    "executedQty": "0.001",
    "avgPrice": "50000.00",
    "price": "0",
    "stopPrice": "0",
    "updateTime": 1_700_000_000_000,
}

LIMIT_ORDER_RAW = {
    "orderId": 100002,
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "status": "NEW",
    "executedQty": "0.0",
    "avgPrice": "0",
    "price": "48000.00",
    "stopPrice": "0",
    "updateTime": 1_700_000_000_000,
}

STOP_ORDER_RAW = {
    "orderId": 100003,
    "symbol": "BTCUSDT",
    "side": "SELL",
    "type": "STOP",
    "status": "NEW",
    "executedQty": "0.0",
    "avgPrice": "0",
    "price": "47000.00",
    "stopPrice": "48000.00",
    "updateTime": 1_700_000_000_000,
}


# ---------------------------------------------------------------------------
# Integration test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_binance() -> AsyncMock:
    """AsyncMock for BinanceClient — reusable across integration tests."""
    mock = AsyncMock()
    mock.place_market_order = AsyncMock(return_value=MARKET_ORDER_RAW)
    mock.place_limit_order = AsyncMock(return_value=LIMIT_ORDER_RAW)
    mock.place_stop_limit_order = AsyncMock(return_value=STOP_ORDER_RAW)
    mock.get_order = AsyncMock(return_value=MARKET_ORDER_RAW)
    return mock


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """
    Lightweight mock of an ``AsyncSession``.

    Used by integration tests to suppress real DB calls while still allowing
    the route handlers to call ``repo.create()``.
    """
    session = AsyncMock()
    session.add = MagicMock()           # synchronous in SQLAlchemy
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest_asyncio.fixture
async def api_client(
    mock_binance: AsyncMock,
    mock_db_session: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP test client wired to the FastAPI app via ASGITransport.

    Both ``get_binance_client`` and ``get_db_session`` are overridden so
    no real API calls or DB writes are made during integration tests.
    """
    _app = create_app()
    _app.dependency_overrides[get_binance_client] = lambda: mock_binance
    _app.dependency_overrides[get_db_session] = lambda: mock_db_session

    async with AsyncClient(
        transport=ASGITransport(app=_app),
        base_url="http://testserver",
    ) as client:
        yield client
