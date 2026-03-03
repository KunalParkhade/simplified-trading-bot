"""Async Binance Futures REST API client.

Wraps ``httpx.AsyncClient`` (injected via DI at request time) with
HMAC-SHA256 request signing, structured logging, and error handling.

The caller is responsible for managing the lifecycle of the
``httpx.AsyncClient`` — typically created at app startup inside the
FastAPI ``lifespan`` context and stored in ``app.state.http_client``.
"""

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.exceptions import BinanceAPIError, OrderNotFoundError

logger = logging.getLogger(__name__)


class BinanceClient:
    """
    Async client for the Binance Futures Testnet REST API.

    Reuses a shared ``httpx.AsyncClient`` for connection pooling.
    Signs every private request with HMAC-SHA256.

    Args:
        api_key: Binance API key.
        api_secret: Binance API secret used for HMAC signing.
        base_url: Binance Futures base URL.
        http_client: Shared ``httpx.AsyncClient`` from application state.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        if not api_key:
            raise ValueError("Binance API key must not be empty.")
        if not api_secret:
            raise ValueError("Binance API secret must not be empty.")

        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._client = http_client
        logger.debug("BinanceClient initialised (base_url=%s)", self._base_url)

    # ------------------------------------------------------------------
    # Public order methods
    # ------------------------------------------------------------------

    async def place_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> dict[str, Any]:
        """Place a MARKET order and return the raw API response."""
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "MARKET",
            "quantity": quantity,
        }
        logger.info(
            "Placing MARKET order | symbol=%s side=%s quantity=%s",
            symbol, side, quantity,
        )
        return await self._signed_post("/fapi/v1/order", params)

    async def place_limit_order(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> dict[str, Any]:
        """Place a LIMIT order (GTC) and return the raw API response."""
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": quantity,
            "price": price,
            "timeInForce": "GTC",
        }
        logger.info(
            "Placing LIMIT order | symbol=%s side=%s quantity=%s price=%s",
            symbol, side, quantity, price,
        )
        return await self._signed_post("/fapi/v1/order", params)

    async def place_stop_limit_order(
        self, symbol: str, side: str, quantity: float, price: float, stop_price: float
    ) -> dict[str, Any]:
        """Place a STOP-LIMIT order (GTC) and return the raw API response."""
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "STOP",
            "quantity": quantity,
            "price": price,
            "stopPrice": stop_price,
            "timeInForce": "GTC",
        }
        logger.info(
            "Placing STOP order | symbol=%s side=%s quantity=%s price=%s stopPrice=%s",
            symbol, side, quantity, price, stop_price,
        )
        return await self._signed_post("/fapi/v1/order", params)

    async def get_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Query an existing order by ID. Raises :exc:`OrderNotFoundError` if absent."""
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "orderId": order_id,
        }
        logger.info("Querying order | symbol=%s orderId=%s", symbol, order_id)
        result = await self._signed_get("/fapi/v1/order", params)
        if not result:
            raise OrderNotFoundError(order_id, symbol)
        return result

    # ------------------------------------------------------------------
    # Private signing & HTTP helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """Stamp params with the current timestamp and an HMAC-SHA256 signature."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode(),
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    async def _signed_post(
        self, path: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        signed = self._sign(params)
        url = self._base_url + path
        response = await self._client.post(
            url,
            data=signed,
            headers={"X-MBX-APIKEY": self._api_key},
        )
        return self._handle_response(response)

    async def _signed_get(
        self, path: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        signed = self._sign(params)
        url = self._base_url + path
        response = await self._client.get(
            url,
            params=signed,
            headers={"X-MBX-APIKEY": self._api_key},
        )
        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: httpx.Response) -> dict[str, Any]:
        """Parse the response and raise :exc:`BinanceAPIError` on failure."""
        try:
            data: dict[str, Any] = response.json()
        except Exception:
            response.raise_for_status()
            return {}

        if not response.is_success:
            code = int(data.get("code", response.status_code))
            message = str(data.get("msg", response.text))
            raise BinanceAPIError(code=code, message=message)

        return data
