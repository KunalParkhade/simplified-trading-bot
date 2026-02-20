"""
Order placement logic and response formatting for Binance Futures Testnet.

Wraps the low-level :class:`~bot.client.BinanceClient` calls with
business-level logging and structures the raw API response into a
normalised :class:`OrderResult` object.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bot.client import BinanceClient

logger = logging.getLogger(__name__)


@dataclass
class OrderResult:
    """Normalised representation of a placed order."""

    order_id: int
    symbol: str
    side: str
    order_type: str
    status: str
    executed_qty: float
    avg_price: float
    timestamp: datetime

    def __str__(self) -> str:
        time_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "=" * 40,
            "ORDER RESPONSE",
            "=" * 40,
            f"Order ID:     {self.order_id}",
            f"Status:       {self.status}",
            f"Executed Qty: {self.executed_qty}",
            f"Avg Price:    {self.avg_price:.2f} USDT",
            f"Time:         {time_str}",
            "=" * 40,
        ]
        return "\n".join(lines)


def _parse_response(raw: dict[str, Any], order_type: str) -> OrderResult:
    """
    Convert a raw Binance API order response into an :class:`OrderResult`.

    Args:
        raw: Raw JSON dict returned by the Binance API.
        order_type: ``MARKET`` or ``LIMIT`` (used as fallback if absent from response).

    Returns:
        Parsed :class:`OrderResult`.
    """
    order_id: int = int(raw.get("orderId", 0))
    symbol: str = raw.get("symbol", "")
    side: str = raw.get("side", "")
    status: str = raw.get("status", "")
    executed_qty: float = float(raw.get("executedQty", 0))

    # avgPrice is present for MARKET fills; use price for LIMIT orders
    avg_price_raw = raw.get("avgPrice") or raw.get("price") or "0"
    avg_price: float = float(avg_price_raw)

    # updateTime is milliseconds since epoch
    update_time_ms: int = int(raw.get("updateTime", 0))
    if update_time_ms:
        timestamp = datetime.fromtimestamp(update_time_ms / 1000, tz=timezone.utc)
    else:
        timestamp = datetime.now(tz=timezone.utc)

    return OrderResult(
        order_id=order_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        status=status,
        executed_qty=executed_qty,
        avg_price=avg_price,
        timestamp=timestamp,
    )


def execute_market_order(
    client: BinanceClient, symbol: str, side: str, quantity: float
) -> OrderResult:
    """
    Execute a MARKET order via the Binance Futures Testnet API.

    Args:
        client: Authenticated :class:`~bot.client.BinanceClient` instance.
        symbol: Trading pair (e.g. ``BTCUSDT``).
        side: ``BUY`` or ``SELL``.
        quantity: Quantity to trade.

    Returns:
        :class:`OrderResult` with order details.

    Raises:
        :class:`~bot.client.BinanceAPIError`: On API-level failures.
        :class:`requests.exceptions.RequestException`: On network failures.
    """
    logger.info(
        "Executing MARKET order | symbol=%s side=%s quantity=%s",
        symbol,
        side,
        quantity,
    )
    raw = client.place_market_order(symbol, side, quantity)
    result = _parse_response(raw, "MARKET")
    logger.info(
        "MARKET order placed | order_id=%s status=%s executed_qty=%s avg_price=%s",
        result.order_id,
        result.status,
        result.executed_qty,
        result.avg_price,
    )
    return result


def execute_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
) -> OrderResult:
    """
    Execute a LIMIT order via the Binance Futures Testnet API.

    Args:
        client: Authenticated :class:`~bot.client.BinanceClient` instance.
        symbol: Trading pair (e.g. ``ETHUSDT``).
        side: ``BUY`` or ``SELL``.
        quantity: Quantity to trade.
        price: Limit price.

    Returns:
        :class:`OrderResult` with order details.

    Raises:
        :class:`~bot.client.BinanceAPIError`: On API-level failures.
        :class:`requests.exceptions.RequestException`: On network failures.
    """
    logger.info(
        "Executing LIMIT order | symbol=%s side=%s quantity=%s price=%s",
        symbol,
        side,
        quantity,
        price,
    )
    raw = client.place_limit_order(symbol, side, quantity, price)
    result = _parse_response(raw, "LIMIT")
    logger.info(
        "LIMIT order placed | order_id=%s status=%s executed_qty=%s price=%s",
        result.order_id,
        result.status,
        result.executed_qty,
        price,
    )
    return result
