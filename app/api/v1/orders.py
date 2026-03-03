"""Orders API — v1 routes.

Endpoints
---------
POST  /api/v1/orders/           Place a new MARKET, LIMIT, or STOP order.
GET   /api/v1/orders/           List persisted orders (paginated, optional symbol filter).
GET   /api/v1/orders/{order_id} Query an existing order by Binance orderId.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query

from app.core.exceptions import OrderValidationError
from app.db.repository import OrderRepository
from app.dependencies import BinanceClientDep, DBSessionDep
from app.schemas.order import OrderListResponse, OrderResponse, OrderType, PlaceOrderRequest

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
    session: DBSessionDep,
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
            result = _parse_order_response(raw, "MARKET")

        case OrderType.LIMIT:
            if body.price is None:
                raise OrderValidationError("'price' is required for LIMIT orders.")
            raw = await client.place_limit_order(
                body.symbol, body.side.value, body.quantity, body.price
            )
            result = _parse_order_response(raw, "LIMIT")

        case OrderType.STOP:
            if body.price is None or body.stop_price is None:
                raise OrderValidationError(
                    "'price' and 'stop_price' are required for STOP orders."
                )
            raw = await client.place_stop_limit_order(
                body.symbol, body.side.value, body.quantity, body.price, body.stop_price
            )
            result = _parse_order_response(raw, "STOP", stop_price=body.stop_price)

        case _:  # pragma: no cover — guarded by schema enum
            raise OrderValidationError(
                f"Unsupported order type: {body.order_type.value!r}"
            )

    await OrderRepository(session).create(result)
    logger.info("Order persisted | order_id=%s symbol=%s", result.order_id, result.symbol)
    return result


@router.get(
    "/",
    response_model=OrderListResponse,
    summary="List persisted orders",
    description=(
        "Return a paginated list of orders that have been placed through this API "
        "and persisted in the local database.  \n\n"
        "Use the optional `symbol` filter to narrow results to a specific trading pair."
    ),
)
async def list_orders(
    session: DBSessionDep,
    symbol: str | None = Query(None, description="Filter by trading pair, e.g. BTCUSDT"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
) -> OrderListResponse:
    repo = OrderRepository(session)
    if symbol:
        rows = await repo.list_by_symbol(symbol.upper(), limit=limit, offset=offset)
    else:
        rows = await repo.list_all(limit=limit, offset=offset)
    items = [OrderResponse.model_validate(row) for row in rows]
    logger.info("List orders | symbol=%s limit=%s offset=%s returned=%s", symbol, limit, offset, len(items))
    return OrderListResponse(total=len(items), limit=limit, offset=offset, items=items)


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
