"""Shared pytest fixtures for Phase 1 test suite.

Strategy
--------
- Unit tests use direct imports and `respx` for httpx mocking.
- Integration tests use ``httpx.ASGITransport`` to drive the FastAPI app
  entirely in-process (no real network calls, no real Binance API needed).
- The ``get_binance_client`` dependency is overridden in integration tests
  with an ``AsyncMock`` so all routes are exercised without touching the
  real Binance API.
"""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_binance_client
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


@pytest_asyncio.fixture
async def api_client(mock_binance: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP test client wired to the FastAPI app via ASGITransport.

    The ``get_binance_client`` dependency is overridden to inject
    ``mock_binance``, so no real Binance API calls are made.
    """
    _app = create_app()
    _app.dependency_overrides[get_binance_client] = lambda: mock_binance

    async with AsyncClient(
        transport=ASGITransport(app=_app),
        base_url="http://testserver",
    ) as client:
        yield client
