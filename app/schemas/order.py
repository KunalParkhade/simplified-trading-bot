"""Pydantic v2 request/response schemas for the Orders API."""

import re
from datetime import datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}$")


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class PlaceOrderRequest(BaseModel):
    """Request body for placing a new order."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str = Field(..., description="Trading pair symbol, e.g. BTCUSDT")
    side: OrderSide = Field(..., description="BUY or SELL")
    order_type: OrderType = Field(
        ..., alias="type", description="MARKET, LIMIT, or STOP"
    )
    quantity: float = Field(..., gt=0, description="Order quantity (must be > 0)")
    price: float | None = Field(
        None, gt=0, description="Limit price — required for LIMIT and STOP orders"
    )
    stop_price: float | None = Field(
        None, gt=0, description="Trigger price — required for STOP orders"
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def normalise_symbol(cls, v: str) -> str:
        upper = str(v).upper()
        if not _SYMBOL_RE.match(upper):
            raise ValueError(
                f"Invalid symbol '{v}'. "
                "Must be 2–20 uppercase alphanumeric characters (e.g. BTCUSDT)."
            )
        return upper

    @model_validator(mode="after")
    def check_price_requirements(self) -> Self:
        if self.order_type in (OrderType.LIMIT, OrderType.STOP) and self.price is None:
            raise ValueError(
                f"'price' is required for {self.order_type.value} orders."
            )
        if self.order_type == OrderType.STOP and self.stop_price is None:
            raise ValueError("'stop_price' is required for STOP orders.")
        return self


class OrderResponse(BaseModel):
    """Normalised response returned after placing or querying an order."""

    model_config = ConfigDict(from_attributes=True)

    order_id: int
    symbol: str
    side: str
    order_type: str
    status: str
    executed_qty: float
    avg_price: float
    stop_price: float = 0.0
    timestamp: datetime


class OrderListResponse(BaseModel):
    """Paginated list of persisted orders."""

    total: int = Field(..., description="Total number of orders matching the filter")
    limit: int = Field(..., description="Page size used for this response")
    offset: int = Field(..., description="Number of records skipped")
    items: list[OrderResponse] = Field(..., description="Orders for this page")
