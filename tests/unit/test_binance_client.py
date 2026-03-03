"""Unit tests for BinanceClient — httpx calls mocked via respx."""

import json

import httpx
import pytest
import respx

from app.core.exceptions import BinanceAPIError, OrderNotFoundError
from app.services.binance_client import BinanceClient

BASE_URL = "https://testnet.binancefuture.com"


def _make_client() -> tuple[BinanceClient, httpx.AsyncClient]:
    """Create a BinanceClient backed by a real (un-sent) AsyncClient."""
    http = httpx.AsyncClient()
    client = BinanceClient(
        api_key="test_api_key",
        api_secret="test_api_secret",
        base_url=BASE_URL,
        http_client=http,
    )
    return client, http


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

class TestBinanceClientInit:
    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="API key"):
            BinanceClient("", "secret", BASE_URL, httpx.AsyncClient())

    def test_empty_api_secret_raises(self):
        with pytest.raises(ValueError, match="API secret"):
            BinanceClient("key", "", BASE_URL, httpx.AsyncClient())

    def test_valid_credentials_create_client(self):
        c, _ = _make_client()
        assert c._api_key == "test_api_key"
        assert c._base_url == BASE_URL  # trailing slash stripped


# ---------------------------------------------------------------------------
# HMAC signing
# ---------------------------------------------------------------------------

class TestBinanceClientSigning:
    def test_sign_adds_timestamp_and_signature(self):
        client, _ = _make_client()
        params = {"symbol": "BTCUSDT", "side": "BUY"}
        signed = client._sign(params)
        assert "timestamp" in signed
        assert "signature" in signed
        assert len(signed["signature"]) == 64  # SHA-256 hex digest is 64 chars

    def test_sign_is_deterministic_given_same_timestamp(self):
        """Two sign calls with the same payload+timestamp produce the same sig."""
        import hmac as _hmac
        import hashlib
        from urllib.parse import urlencode

        secret = "test_api_secret"
        params = {"symbol": "BTCUSDT", "timestamp": 1_700_000_000_000}
        qs = urlencode(params)
        expected = _hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
        assert expected == _hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# place_market_order
# ---------------------------------------------------------------------------

MARKET_RESPONSE = {
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

LIMIT_RESPONSE = {
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

STOP_RESPONSE = {
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


class TestPlaceMarketOrder:
    @respx.mock
    async def test_success_returns_raw_dict(self):
        respx.post(f"{BASE_URL}/fapi/v1/order").mock(
            return_value=httpx.Response(200, json=MARKET_RESPONSE)
        )
        client, http = _make_client()
        async with http:
            result = await client.place_market_order("BTCUSDT", "BUY", 0.001)
        assert result["orderId"] == 100001
        assert result["status"] == "FILLED"

    @respx.mock
    async def test_api_error_raises_binance_api_error(self):
        respx.post(f"{BASE_URL}/fapi/v1/order").mock(
            return_value=httpx.Response(400, json={"code": -1121, "msg": "Invalid symbol."})
        )
        client, http = _make_client()
        with pytest.raises(BinanceAPIError) as exc_info:
            async with http:
                await client.place_market_order("INVALID", "BUY", 0.001)
        assert exc_info.value.code == -1121
        assert "Invalid symbol" in exc_info.value.message


class TestPlaceLimitOrder:
    @respx.mock
    async def test_success_returns_raw_dict(self):
        respx.post(f"{BASE_URL}/fapi/v1/order").mock(
            return_value=httpx.Response(200, json=LIMIT_RESPONSE)
        )
        client, http = _make_client()
        async with http:
            result = await client.place_limit_order("BTCUSDT", "BUY", 0.001, 48000)
        assert result["orderId"] == 100002
        assert result["type"] == "LIMIT"


class TestPlaceStopLimitOrder:
    @respx.mock
    async def test_success_returns_raw_dict(self):
        respx.post(f"{BASE_URL}/fapi/v1/order").mock(
            return_value=httpx.Response(200, json=STOP_RESPONSE)
        )
        client, http = _make_client()
        async with http:
            result = await client.place_stop_limit_order("BTCUSDT", "SELL", 0.001, 47000, 48000)
        assert result["orderId"] == 100003
        assert result["stopPrice"] == "48000.00"


class TestGetOrder:
    @respx.mock
    async def test_success_returns_raw_dict(self):
        respx.get(f"{BASE_URL}/fapi/v1/order").mock(
            return_value=httpx.Response(200, json=MARKET_RESPONSE)
        )
        client, http = _make_client()
        async with http:
            result = await client.get_order("BTCUSDT", 100001)
        assert result["orderId"] == 100001

    @respx.mock
    async def test_404_raises_binance_api_error(self):
        respx.get(f"{BASE_URL}/fapi/v1/order").mock(
            return_value=httpx.Response(400, json={"code": -2013, "msg": "Order does not exist."})
        )
        client, http = _make_client()
        with pytest.raises(BinanceAPIError) as exc_info:
            async with http:
                await client.get_order("BTCUSDT", 99999)
        assert exc_info.value.code == -2013


class TestHandleResponse:
    def test_success_response_returns_dict(self):
        client, _ = _make_client()
        resp = httpx.Response(200, json={"orderId": 1})
        assert client._handle_response(resp) == {"orderId": 1}

    def test_error_response_raises_binance_api_error(self):
        client, _ = _make_client()
        resp = httpx.Response(400, json={"code": -1100, "msg": "Illegal characters."})
        with pytest.raises(BinanceAPIError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.code == -1100
        assert "Illegal characters" in exc_info.value.message

    def test_error_response_uses_http_status_when_no_code(self):
        client, _ = _make_client()
        resp = httpx.Response(502, json={"msg": "Gateway error"})
        with pytest.raises(BinanceAPIError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.code == 502
