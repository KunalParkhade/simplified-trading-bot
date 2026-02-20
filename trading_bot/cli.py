#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet trading bot.

Usage examples::

    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

    python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3500.50
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import setup_logging
from bot.orders import execute_limit_order, execute_market_order
from bot.validators import validate_order_inputs

# Initialise logging before anything else
setup_logging()
logger = logging.getLogger(__name__)


def _print_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None,
) -> None:
    lines = [
        "=" * 40,
        "ORDER REQUEST SUMMARY",
        "=" * 40,
        f"Symbol:       {symbol}",
        f"Side:         {side}",
        f"Type:         {order_type}",
        f"Quantity:     {quantity}",
    ]
    if price is not None:
        lines.append(f"Price:        {price}")
    lines.append("=" * 40)
    print("\n".join(lines))


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Place orders on Binance Futures Testnet.",
    )
    parser.add_argument(
        "--symbol",
        required=True,
        metavar="SYMBOL",
        help="Trading pair symbol, e.g. BTCUSDT.",
    )
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        metavar="SIDE",
        help="Order side: BUY or SELL.",
    )
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT"],
        metavar="TYPE",
        help="Order type: MARKET or LIMIT.",
    )
    parser.add_argument(
        "--quantity",
        required=True,
        type=float,
        metavar="QTY",
        help="Order quantity (positive number).",
    )
    parser.add_argument(
        "--price",
        type=float,
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT orders).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    symbol: str = args.symbol.upper()
    side: str = args.side.upper()
    order_type: str = args.order_type.upper()
    quantity: float = args.quantity
    price: float | None = args.price

    # ------------------------------------------------------------------ #
    # Validate inputs                                                       #
    # ------------------------------------------------------------------ #
    try:
        validate_order_inputs(symbol, side, order_type, quantity, price)
    except ValueError as exc:
        logger.error("Validation error: %s", exc)
        print(f"\n[ERROR] {exc}\n", file=sys.stderr)
        return 1

    _print_request_summary(symbol, side, order_type, quantity, price)
    print("\nPlacing order...\n")

    # ------------------------------------------------------------------ #
    # Build client                                                          #
    # ------------------------------------------------------------------ #
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    base_url = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")

    if not api_key or not api_secret:
        msg = (
            "BINANCE_API_KEY and BINANCE_API_SECRET must be set. "
            "Copy .env.example to .env and fill in your credentials."
        )
        logger.error(msg)
        print(f"\n[ERROR] {msg}\n", file=sys.stderr)
        return 1

    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret, base_url=base_url)
    except ValueError as exc:
        logger.error("Client initialisation error: %s", exc)
        print(f"\n[ERROR] {exc}\n", file=sys.stderr)
        return 1

    # ------------------------------------------------------------------ #
    # Place order                                                           #
    # ------------------------------------------------------------------ #
    try:
        if order_type == "MARKET":
            result = execute_market_order(client, symbol, side, quantity)
        else:
            result = execute_limit_order(client, symbol, side, quantity, price)  # type: ignore[arg-type]
    except BinanceAPIError as exc:
        _handle_api_error(exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while placing order")
        print(f"\n[ERROR] Unexpected error: {exc}\n", file=sys.stderr)
        return 1

    print(result)
    print("✓ Order placed successfully!")
    return 0


def _handle_api_error(exc: BinanceAPIError) -> None:
    """Print a user-friendly error message for API errors."""
    logger.error("API error %s: %s", exc.code, exc.message)

    friendly: dict[int, str] = {
        -1003: "Rate limit exceeded. Please wait before retrying.",
        -2010: "Insufficient balance to place this order.",
        -1121: "Invalid symbol. Check that the trading pair exists on the testnet.",
        -1100: "Illegal characters in parameter. Check your inputs.",
        -1102: "A mandatory parameter is missing.",
        -2011: "Unknown order. The order may not exist.",
        401: "Authentication failed. Check your API key and secret.",
    }
    user_msg = friendly.get(exc.code, f"API error {exc.code}: {exc.message}")
    print(f"\n[ERROR] {user_msg}\n", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
