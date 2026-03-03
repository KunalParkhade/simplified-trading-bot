"""Unit tests for domain exception classes."""

import pytest

from app.core.exceptions import (
    BinanceAPIError,
    ConfigurationError,
    OrderNotFoundError,
    OrderValidationError,
    TradingBotError,
)


class TestBinanceAPIError:
    def test_attributes_stored(self):
        exc = BinanceAPIError(code=-1121, message="Invalid symbol.")
        assert exc.code == -1121
        assert exc.message == "Invalid symbol."

    def test_str_includes_code_and_message(self):
        exc = BinanceAPIError(code=-2011, message="Unknown order sent.")
        assert "-2011" in str(exc)
        assert "Unknown order sent." in str(exc)

    def test_is_trading_bot_error(self):
        exc = BinanceAPIError(code=400, message="Bad request")
        assert isinstance(exc, TradingBotError)
        assert isinstance(exc, Exception)


class TestOrderValidationError:
    def test_message_preserved(self):
        exc = OrderValidationError("'price' is required for LIMIT orders.")
        assert "'price' is required for LIMIT orders." in str(exc)

    def test_is_trading_bot_error(self):
        assert isinstance(OrderValidationError("x"), TradingBotError)


class TestOrderNotFoundError:
    def test_attributes_stored(self):
        exc = OrderNotFoundError(order_id=99, symbol="ETHUSDT")
        assert exc.order_id == 99
        assert exc.symbol == "ETHUSDT"

    def test_str_includes_order_id_and_symbol(self):
        exc = OrderNotFoundError(order_id=42, symbol="BTCUSDT")
        assert "42" in str(exc)
        assert "BTCUSDT" in str(exc)

    def test_is_trading_bot_error(self):
        assert isinstance(OrderNotFoundError(1, "X"), TradingBotError)


class TestConfigurationError:
    def test_is_trading_bot_error(self):
        assert isinstance(ConfigurationError("missing key"), TradingBotError)

    def test_message_preserved(self):
        exc = ConfigurationError("BINANCE_API_KEY not set")
        assert "BINANCE_API_KEY not set" in str(exc)
