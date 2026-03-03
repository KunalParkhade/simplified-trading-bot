"""Integration tests for POST /api/v1/orders/ and GET /api/v1/orders/{id}."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import BinanceAPIError, OrderNotFoundError
from app.db.models import Order
from app.dependencies import get_binance_client, get_db_session
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# POST /api/v1/orders/  —  happy paths
# ---------------------------------------------------------------------------


class TestPlaceMarketOrderSuccess:
    async def test_returns_201(self, api_client, mock_binance):
        resp = await api_client.post(
            "/api/v1/orders/",
            json={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.001},
        )
        assert resp.status_code == 201

    async def test_returns_order_response_shape(self, api_client, mock_binance):
        resp = await api_client.post(
            "/api/v1/orders/",
            json={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.001},
        )
        data = resp.json()
        assert data["order_id"] == 100001
        assert data["symbol"] == "BTCUSDT"
        assert data["side"] == "BUY"
        assert data["order_type"] == "MARKET"
        assert data["status"] == "FILLED"
        assert data["executed_qty"] == 0.001
        assert data["avg_price"] == 50000.0
        assert "timestamp" in data

    async def test_binance_client_called_with_correct_args(self, api_client, mock_binance):
        await api_client.post(
            "/api/v1/orders/",
            json={"symbol": "btcusdt", "side": "BUY", "type": "MARKET", "quantity": 0.005},
        )
        mock_binance.place_market_order.assert_called_once_with("BTCUSDT", "BUY", 0.005)


class TestPlaceLimitOrderSuccess:
    async def test_returns_201(self, api_client):
        resp = await api_client.post(
            "/api/v1/orders/",
            json={"symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "quantity": 0.001, "price": 48000},
        )
        assert resp.status_code == 201

    async def test_returns_limit_order_response(self, api_client, mock_binance):
        resp = await api_client.post(
            "/api/v1/orders/",
            json={"symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "quantity": 0.001, "price": 48000},
        )
        data = resp.json()
        assert data["order_id"] == 100002
        assert data["order_type"] == "LIMIT"

    async def test_binance_client_called_with_correct_args(self, api_client, mock_binance):
        await api_client.post(
            "/api/v1/orders/",
            json={"symbol": "ETHUSDT", "side": "SELL", "type": "LIMIT", "quantity": 1.0, "price": 3500},
        )
        mock_binance.place_limit_order.assert_called_once_with("ETHUSDT", "SELL", 1.0, 3500.0)


class TestPlaceStopOrderSuccess:
    async def test_returns_201(self, api_client):
        resp = await api_client.post(
            "/api/v1/orders/",
            json={
                "symbol": "BTCUSDT", "side": "SELL", "type": "STOP",
                "quantity": 0.001, "price": 47000, "stop_price": 48000,
            },
        )
        assert resp.status_code == 201

    async def test_returns_stop_order_response(self, api_client, mock_binance):
        resp = await api_client.post(
            "/api/v1/orders/",
            json={
                "symbol": "BTCUSDT", "side": "SELL", "type": "STOP",
                "quantity": 0.001, "price": 47000, "stop_price": 48000,
            },
        )
        data = resp.json()
        assert data["order_id"] == 100003
        assert data["order_type"] == "STOP"
        assert data["stop_price"] == 48000.0

    async def test_binance_client_called_with_correct_args(self, api_client, mock_binance):
        await api_client.post(
            "/api/v1/orders/",
            json={
                "symbol": "BTCUSDT", "side": "SELL", "type": "STOP",
                "quantity": 0.001, "price": 47000, "stop_price": 48000,
            },
        )
        mock_binance.place_stop_limit_order.assert_called_once_with(
            "BTCUSDT", "SELL", 0.001, 47000.0, 48000.0
        )


# ---------------------------------------------------------------------------
# POST /api/v1/orders/  —  validation error paths (422)
# ---------------------------------------------------------------------------


class TestPlaceOrderValidationErrors:
    """All 422 paths produce {"error": "validation_error", "detail": [...]}."""

    async def _assert_422(self, api_client, body: dict) -> dict:
        resp = await api_client.post("/api/v1/orders/", json=body)
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"] == "validation_error"
        assert isinstance(data["detail"], list)
        return data

    async def test_limit_missing_price(self, api_client):
        await self._assert_422(
            api_client,
            {"symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "quantity": 0.001},
        )

    async def test_stop_missing_stop_price(self, api_client):
        await self._assert_422(
            api_client,
            {"symbol": "BTCUSDT", "side": "BUY", "type": "STOP", "quantity": 0.001, "price": 47000},
        )

    async def test_stop_missing_both_prices(self, api_client):
        await self._assert_422(
            api_client,
            {"symbol": "BTCUSDT", "side": "BUY", "type": "STOP", "quantity": 0.001},
        )

    async def test_zero_quantity(self, api_client):
        await self._assert_422(
            api_client,
            {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0},
        )

    async def test_negative_quantity(self, api_client):
        await self._assert_422(
            api_client,
            {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": -1},
        )

    async def test_invalid_symbol(self, api_client):
        await self._assert_422(
            api_client,
            {"symbol": "BTC USDT!", "side": "BUY", "type": "MARKET", "quantity": 0.001},
        )

    async def test_invalid_side(self, api_client):
        await self._assert_422(
            api_client,
            {"symbol": "BTCUSDT", "side": "HOLD", "type": "MARKET", "quantity": 0.001},
        )

    async def test_invalid_order_type(self, api_client):
        await self._assert_422(
            api_client,
            {"symbol": "BTCUSDT", "side": "BUY", "type": "FOO", "quantity": 0.001},
        )

    async def test_missing_required_fields(self, api_client):
        await self._assert_422(api_client, {})

    async def test_negative_price(self, api_client):
        await self._assert_422(
            api_client,
            {"symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "quantity": 0.001, "price": -1},
        )


# ---------------------------------------------------------------------------
# POST /api/v1/orders/  —  upstream Binance API error (502)
# ---------------------------------------------------------------------------


class TestPlaceOrderBinanceError:
    async def test_binance_error_returns_502(self, api_client, mock_binance):
        mock_binance.place_market_order.side_effect = BinanceAPIError(
            code=-1121, message="Invalid symbol."
        )
        resp = await api_client.post(
            "/api/v1/orders/",
            json={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.001},
        )
        assert resp.status_code == 502

    async def test_binance_error_returns_correct_error_envelope(self, api_client, mock_binance):
        mock_binance.place_market_order.side_effect = BinanceAPIError(
            code=-1121, message="Invalid symbol."
        )
        data = (
            await api_client.post(
                "/api/v1/orders/",
                json={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.001},
            )
        ).json()
        assert data["error"] == "binance_api_error"
        assert "-1121" in data["detail"]
        assert "Invalid symbol" in data["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/orders/{order_id}  —  happy path
# ---------------------------------------------------------------------------


class TestGetOrderSuccess:
    async def test_returns_200(self, api_client):
        resp = await api_client.get("/api/v1/orders/100001?symbol=BTCUSDT")
        assert resp.status_code == 200

    async def test_returns_order_response_shape(self, api_client):
        data = (await api_client.get("/api/v1/orders/100001?symbol=BTCUSDT")).json()
        assert data["order_id"] == 100001
        assert data["symbol"] == "BTCUSDT"
        assert "timestamp" in data

    async def test_binance_client_called_with_correct_args(self, api_client, mock_binance):
        await api_client.get("/api/v1/orders/100001?symbol=btcusdt")
        mock_binance.get_order.assert_called_once_with("BTCUSDT", 100001)


# ---------------------------------------------------------------------------
# GET /api/v1/orders/{order_id}  —  order not found (404)
# ---------------------------------------------------------------------------


class TestGetOrderNotFound:
    async def test_order_not_found_returns_404(self, api_client, mock_binance):
        mock_binance.get_order.side_effect = OrderNotFoundError(99999, "BTCUSDT")
        resp = await api_client.get("/api/v1/orders/99999?symbol=BTCUSDT")
        assert resp.status_code == 404

    async def test_order_not_found_error_envelope(self, api_client, mock_binance):
        mock_binance.get_order.side_effect = OrderNotFoundError(99999, "BTCUSDT")
        data = (await api_client.get("/api/v1/orders/99999?symbol=BTCUSDT")).json()
        assert data["error"] == "order_not_found"
        assert "99999" in data["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/orders/{order_id}  —  missing symbol query param (422)
# ---------------------------------------------------------------------------


class TestGetOrderMissingSymbol:
    async def test_missing_symbol_returns_422(self, api_client):
        resp = await api_client.get("/api/v1/orders/100001")
        assert resp.status_code == 422
        assert resp.json()["error"] == "validation_error"


# ---------------------------------------------------------------------------
# 503 — no Binance credentials configured
# ---------------------------------------------------------------------------


class TestMissingCredentials:
    async def test_returns_503_when_credentials_missing(self):
        """A fresh app whose Settings have empty credentials must return 503.

        We override ``get_settings`` (not ``get_binance_client``) so the
        credential-guard in the dependency fires *before* any access to
        ``app.state.http_client``.
        """
        from app.config import Settings, get_settings

        _app = create_app()
        empty_settings = Settings(binance_api_key="", binance_api_secret="")
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.execute = AsyncMock()
        _app.dependency_overrides[get_settings] = lambda: empty_settings
        _app.dependency_overrides[get_db_session] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=_app),
            base_url="http://testserver",
        ) as client:
            resp = await client.post(
                "/api/v1/orders/",
                json={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.001},
            )
        assert resp.status_code == 503
        assert "credentials" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /api/v1/orders/  —  list endpoint
# ---------------------------------------------------------------------------


def _make_db_order(**overrides) -> Order:
    """Build an ``Order`` ORM instance (not persisted) for mocking results."""
    defaults = dict(
        id=1,
        order_id=100001,
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        status="FILLED",
        executed_qty=0.001,
        avg_price=50000.0,
        stop_price=0.0,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    obj = Order.__new__(Order)
    obj.__dict__.update(defaults)
    return obj


class TestListOrders:
    """Tests for GET /api/v1/orders/ with a mocked DB session."""

    def _make_client_with_repo_mock(self, mock_binance, mock_db_session, list_result):
        """Return (app, session overrides) wiring up both BinanceClient and repo."""
        from sqlalchemy.engine.result import MappingResult
        from unittest.mock import patch

        _app = create_app()
        _app.dependency_overrides[get_binance_client] = lambda: mock_binance
        _app.dependency_overrides[get_db_session] = lambda: mock_db_session
        return _app

    async def test_list_orders_returns_200(self, api_client, mock_db_session):
        # list_all returns empty list via scalars().all() — patch at repo level
        from app.db import repository as repo_mod
        from unittest.mock import patch, AsyncMock as AM

        async def fake_list_all(self, **kwargs):
            return []

        with patch.object(repo_mod.OrderRepository, "list_all", fake_list_all):
            resp = await api_client.get("/api/v1/orders/")
        assert resp.status_code == 200

    async def test_list_orders_response_shape(self, api_client, mock_db_session):
        from app.db import repository as repo_mod
        from unittest.mock import patch

        async def fake_list_all(self, **kwargs):
            return []

        with patch.object(repo_mod.OrderRepository, "list_all", fake_list_all):
            data = (await api_client.get("/api/v1/orders/")).json()

        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_list_orders_returns_orders(self, api_client, mock_db_session):
        from app.db import repository as repo_mod
        from unittest.mock import patch

        orders = [_make_db_order(id=i, order_id=100000 + i) for i in range(1, 4)]

        async def fake_list_all(self, **kwargs):
            return orders

        with patch.object(repo_mod.OrderRepository, "list_all", fake_list_all):
            data = (await api_client.get("/api/v1/orders/")).json()

        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_orders_symbol_filter_calls_list_by_symbol(self, api_client, mock_db_session):
        from app.db import repository as repo_mod
        from unittest.mock import patch

        called_with = {}

        async def fake_list_by_symbol(self, symbol, **kwargs):
            called_with["symbol"] = symbol
            return []

        with patch.object(repo_mod.OrderRepository, "list_by_symbol", fake_list_by_symbol):
            resp = await api_client.get("/api/v1/orders/?symbol=ETHUSDT")

        assert resp.status_code == 200
        assert called_with.get("symbol") == "ETHUSDT"

    async def test_list_orders_default_pagination(self, api_client, mock_db_session):
        from app.db import repository as repo_mod
        from unittest.mock import patch

        async def fake_list_all(self, **kwargs):
            return []

        with patch.object(repo_mod.OrderRepository, "list_all", fake_list_all):
            data = (await api_client.get("/api/v1/orders/")).json()

        assert data["limit"] == 50
        assert data["offset"] == 0

    async def test_list_orders_custom_pagination(self, api_client, mock_db_session):
        from app.db import repository as repo_mod
        from unittest.mock import patch

        async def fake_list_all(self, **kwargs):
            return []

        with patch.object(repo_mod.OrderRepository, "list_all", fake_list_all):
            data = (await api_client.get("/api/v1/orders/?limit=10&offset=5")).json()

        assert data["limit"] == 10
        assert data["offset"] == 5

    async def test_list_orders_limit_too_large_returns_422(self, api_client):
        resp = await api_client.get("/api/v1/orders/?limit=999")
        assert resp.status_code == 422

    async def test_list_orders_negative_offset_returns_422(self, api_client):
        resp = await api_client.get("/api/v1/orders/?offset=-1")
        assert resp.status_code == 422
