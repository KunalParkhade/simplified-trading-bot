"""
Input validation for the trading bot CLI.

All validator functions return ``None`` on success and raise
:class:`ValueError` with a user-friendly message on failure.
"""

import re

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}

# Binance symbol: 2-10 uppercase letters/digits (e.g. BTCUSDT, ETHUSDT)
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}$")


def validate_symbol(symbol: str) -> None:
    """
    Validate a Binance trading pair symbol.

    Args:
        symbol: The symbol string to validate (e.g. ``BTCUSDT``).

    Raises:
        ValueError: If the symbol is not a non-empty alphanumeric uppercase string.
    """
    if not symbol or not _SYMBOL_RE.match(symbol.upper()):
        raise ValueError(
            f"Invalid symbol '{symbol}'. "
            "Symbol must be an uppercase alphanumeric string (e.g. BTCUSDT, ETHUSDT)."
        )


def validate_side(side: str) -> None:
    """
    Validate the order side.

    Args:
        side: The side string to validate.

    Raises:
        ValueError: If the side is not ``BUY`` or ``SELL``.
    """
    if side.upper() not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )


def validate_order_type(order_type: str) -> None:
    """
    Validate the order type.

    Args:
        order_type: The order type string to validate.

    Raises:
        ValueError: If the order type is not ``MARKET`` or ``LIMIT``.
    """
    if order_type.upper() not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )


def validate_quantity(quantity: float) -> None:
    """
    Validate the order quantity.

    Args:
        quantity: The quantity value to validate.

    Raises:
        ValueError: If the quantity is not a positive number.
    """
    if quantity <= 0:
        raise ValueError(
            f"Invalid quantity '{quantity}'. Quantity must be a positive number."
        )


def validate_price(price: float) -> None:
    """
    Validate the order price (used for LIMIT orders).

    Args:
        price: The price value to validate.

    Raises:
        ValueError: If the price is not a positive number.
    """
    if price <= 0:
        raise ValueError(
            f"Invalid price '{price}'. Price must be a positive number."
        )


def validate_order_inputs(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None = None,
) -> None:
    """
    Validate all order inputs in one call.

    Args:
        symbol: Trading pair symbol.
        side: ``BUY`` or ``SELL``.
        order_type: ``MARKET`` or ``LIMIT``.
        quantity: Order quantity.
        price: Limit price; required when *order_type* is ``LIMIT``.

    Raises:
        ValueError: On the first validation failure encountered.
    """
    validate_symbol(symbol)
    validate_side(side)
    validate_order_type(order_type)
    validate_quantity(quantity)

    if order_type.upper() == "LIMIT":
        if price is None:
            raise ValueError("Price is required for LIMIT orders.")
        validate_price(price)
