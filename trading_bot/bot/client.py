"""
Binance API client wrapper for Futures Testnet.

Handles authenticated REST requests to the Binance Futures Testnet API,
including request signing and error handling.
"""

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://testnet.binancefuture.com"


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceClient:
    """
    Client for the Binance Futures Testnet REST API.

    Wraps authenticated and unauthenticated endpoints, signs requests,
    and raises :class:`BinanceAPIError` for non-success responses.

    Args:
        api_key: Binance API key (read from ``BINANCE_API_KEY`` env var by default).
        api_secret: Binance API secret (read from ``BINANCE_API_SECRET`` env var by default).
        base_url: Base URL for the Binance Futures Testnet API.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = BASE_URL,
    ) -> None:
        if not api_key:
            raise ValueError("API key must not be empty.")
        if not api_secret:
            raise ValueError("API secret must not be empty.")

        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self._api_key})
        logger.debug("BinanceClient initialised (base_url=%s)", self._base_url)

    # ------------------------------------------------------------------
    # Public order methods
    # ------------------------------------------------------------------

    def place_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> dict[str, Any]:
        """
        Place a MARKET order on Binance Futures Testnet.

        Args:
            symbol: Trading pair symbol (e.g. ``BTCUSDT``).
            side: ``BUY`` or ``SELL``.
            quantity: Quantity to trade.

        Returns:
            Raw response dict from the Binance API.
        """
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "MARKET",
            "quantity": quantity,
        }
        logger.info(
            "Placing MARKET order | symbol=%s side=%s quantity=%s",
            symbol,
            side,
            quantity,
        )
        return self._signed_post("/fapi/v1/order", params)

    def place_limit_order(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> dict[str, Any]:
        """
        Place a LIMIT order on Binance Futures Testnet.

        Args:
            symbol: Trading pair symbol (e.g. ``ETHUSDT``).
            side: ``BUY`` or ``SELL``.
            quantity: Quantity to trade.
            price: Limit price.

        Returns:
            Raw response dict from the Binance API.
        """
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
            symbol,
            side,
            quantity,
            price,
        )
        return self._signed_post("/fapi/v1/order", params)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _signed_post(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a signed POST request and return the parsed JSON body."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        query_string = urlencode(params)
        signature = self._sign(query_string)
        params["signature"] = signature

        url = self._base_url + path
        logger.debug("POST %s | params=%s", path, self._redacted_params(params))
        try:
            response = self._session.post(url, data=params, timeout=10)
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s", exc)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s", exc)
            raise

        return self._handle_response(response)

    def _sign(self, query_string: str) -> str:
        """Create an HMAC-SHA256 signature for the given query string."""
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _handle_response(response: requests.Response) -> dict[str, Any]:
        """Parse the HTTP response and raise :class:`BinanceAPIError` on failure."""
        logger.debug("Response %s: %s", response.status_code, response.text[:500])
        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            logger.error("Failed to parse API response as JSON: %s", exc)
            response.raise_for_status()
            raise

        if response.status_code != 200:
            code = data.get("code", response.status_code)
            message = data.get("msg", response.text)
            logger.error("Binance API error %s: %s", code, message)
            raise BinanceAPIError(code, message)

        return data

    @staticmethod
    def _redacted_params(params: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of params with the signature redacted for safe logging."""
        redacted = dict(params)
        if "signature" in redacted:
            redacted["signature"] = "***"
        return redacted
