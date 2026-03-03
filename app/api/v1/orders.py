"""Orders API — v1 routes.

Endpoints
---------
POST  /api/v1/orders/          Place a new MARKET, LIMIT, or STOP order.
GET   /api/v1/orders/{order_id} Query an existing order by ID.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query

from app.core.exceptions import OrderValidationError
from app.dependencies import BinanceClientDep
from app.schemas.order import OrderResponse, OrderType, PlaceOrderRequest

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_order_response(
    raw: dict[str, Any],
    order_type: str,
    stop_price: float = 0.0,
) -> OrderResponse:
    """Convert a raw Binance API order response into an :class:`OrderResponse`."""
    update_time_ms: int = int(raw.get("updateTime", 0))
    timestamp = (
        datetime.fromtimestamp(update_time_ms / 1000, tz=timezone.utc)
        if update_time_ms
        else datetime.now(tz=timezone.utc)
    )
    avg_price_raw = raw.get("avgPrice") or raw.get("price") or "0"
    return OrderResponse(
        order_id=int(raw.get("orderId", 0)),
        symbol=raw.get("symbol", ""),
        side=raw.get("side", ""),
        order_type=order_type,
        status=raw.get("status", ""),
        executed_qty=float(raw.get("executedQty", 0)),
        avg_price=float(avg_price_raw),
        stop_price=stop_price,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=201,
    summary="Place a new order",
    description=(
        "Place a **MARKET**, **LIMIT**, or **STOP-LIMIT** order on Binance "
        "Futures Testnet.  \n\n"
        "- `MARKET` — only `quantity` required.  \n"
        "- `LIMIT` — requires `quantity` + `price`.  \n"
        "- `STOP` — requires `quantity`, `price`, and `stop_price`."
    ),
)
async def place_order(
    body: PlaceOrderRequest,
    client: BinanceClientDep,
) -> OrderResponse:
    logger.info(
        "Place order request | symbol=%s side=%s type=%s qty=%s",
        body.symbol, body.side.value, body.order_type.value, body.quantity,
    )

    match body.order_type:
        case OrderType.MARKET:
            raw = await client.place_market_order(
                body.symbol, body.side.value, body.quantity
            )
            return _parse_order_response(raw, "MARKET")

        case OrderType.LIMIT:
            if body.price is None:
                raise OrderValidationError("'price' is required for LIMIT orders.")
            raw = await client.place_limit_order(
                body.symbol, body.side.value, body.quantity, body.price
            )
            return _parse_order_response(raw, "LIMIT")

        case OrderType.STOP:
            if body.price is None or body.stop_price is None:
                raise OrderValidationError(
                    "'price' and 'stop_price' are required for STOP orders."
                )
            raw = await client.place_stop_limit_order(
                body.symbol, body.side.value, body.quantity, body.price, body.stop_price
            )
            return _parse_order_response(raw, "STOP", stop_price=body.stop_price)

        case _:  # pragma: no cover — guarded by schema enum
            raise OrderValidationError(
                f"Unsupported order type: {body.order_type.value!r}"
            )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Query an existing order",
    description=(
        "Fetch the current status of an order by its Binance order ID.  \n"
        "The `symbol` query parameter is **required** by the Binance API."
    ),
)
async def get_order(
    order_id: int,
    client: BinanceClientDep,
    symbol: str = Query(..., description="Trading pair symbol, e.g. BTCUSDT"),
) -> OrderResponse:
    logger.info("Get order request | orderId=%s symbol=%s", order_id, symbol)
    raw = await client.get_order(symbol.upper(), order_id)
    return _parse_order_response(
        raw,
        order_type=str(raw.get("type", "UNKNOWN")),
        stop_price=float(raw.get("stopPrice", 0) or 0),
    )
