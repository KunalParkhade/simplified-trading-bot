"""Core domain exceptions for the trading bot."""


class TradingBotError(Exception):
    """Base exception for all trading bot errors."""


class BinanceAPIError(TradingBotError):
    """Raised when the Binance REST API returns a non-success response."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class OrderValidationError(TradingBotError):
    """Raised when order input validation fails (business-level, not Pydantic)."""


class OrderNotFoundError(TradingBotError):
    """Raised when an order cannot be located via the Binance API."""

    def __init__(self, order_id: int, symbol: str) -> None:
        self.order_id = order_id
        self.symbol = symbol
        super().__init__(f"Order {order_id} for symbol {symbol!r} not found.")


class ConfigurationError(TradingBotError):
    """Raised when required application configuration is missing or invalid."""
