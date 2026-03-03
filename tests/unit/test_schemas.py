"""Unit tests for Pydantic v2 request/response schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.order import OrderSide, OrderType, PlaceOrderRequest


class TestPlaceOrderRequestSymbol:
    """Symbol field validation."""

    def test_lowercase_symbol_is_uppercased(self):
        req = PlaceOrderRequest.model_validate(
            {"symbol": "btcusdt", "side": "BUY", "type": "MARKET", "quantity": 0.001}
        )
        assert req.symbol == "BTCUSDT"

    def test_valid_symbol_passes(self):
        req = PlaceOrderRequest.model_validate(
            {"symbol": "ETHUSDT", "side": "SELL", "type": "MARKET", "quantity": 0.1}
        )
        assert req.symbol == "ETHUSDT"

    @pytest.mark.parametrize("bad_symbol", ["", "A", "TOOLONGSYMBOL123456789", "BTC USDT", "btc!"])
    def test_invalid_symbol_raises(self, bad_symbol):
        with pytest.raises(ValidationError) as exc_info:
            PlaceOrderRequest.model_validate(
                {"symbol": bad_symbol, "side": "BUY", "type": "MARKET", "quantity": 0.001}
            )
        assert "Invalid symbol" in str(exc_info.value) or "validation" in str(exc_info.value).lower()


class TestPlaceOrderRequestQuantity:
    """Quantity field validation."""

    @pytest.mark.parametrize("qty", [0, -1, -0.0001])
    def test_non_positive_quantity_raises(self, qty):
        with pytest.raises(ValidationError):
            PlaceOrderRequest.model_validate(
                {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": qty}
            )

    def test_positive_quantity_passes(self):
        req = PlaceOrderRequest.model_validate(
            {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.001}
        )
        assert req.quantity == 0.001


class TestPlaceOrderRequestSide:
    """Side field enum validation."""

    def test_valid_sides(self):
        for side in ("BUY", "SELL"):
            req = PlaceOrderRequest.model_validate(
                {"symbol": "BTCUSDT", "side": side, "type": "MARKET", "quantity": 0.001}
            )
            assert req.side == OrderSide(side)

    def test_invalid_side_raises(self):
        with pytest.raises(ValidationError):
            PlaceOrderRequest.model_validate(
                {"symbol": "BTCUSDT", "side": "HOLD", "type": "MARKET", "quantity": 0.001}
            )


class TestPlaceOrderRequestMarket:
    """MARKET order — price must not be required."""

    def test_market_order_without_price_is_valid(self):
        req = PlaceOrderRequest.model_validate(
            {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.001}
        )
        assert req.order_type == OrderType.MARKET
        assert req.price is None
        assert req.stop_price is None


class TestPlaceOrderRequestLimit:
    """LIMIT order — price is required."""

    def test_limit_order_with_price_is_valid(self):
        req = PlaceOrderRequest.model_validate(
            {"symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "quantity": 0.001, "price": 50000}
        )
        assert req.order_type == OrderType.LIMIT
        assert req.price == 50000.0

    def test_limit_order_without_price_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PlaceOrderRequest.model_validate(
                {"symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "quantity": 0.001}
            )
        assert "price" in str(exc_info.value)

    def test_limit_order_with_negative_price_raises(self):
        with pytest.raises(ValidationError):
            PlaceOrderRequest.model_validate(
                {"symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "quantity": 0.001, "price": -100}
            )


class TestPlaceOrderRequestStop:
    """STOP order — both price and stop_price are required."""

    def test_stop_order_with_both_prices_is_valid(self):
        req = PlaceOrderRequest.model_validate(
            {
                "symbol": "BTCUSDT",
                "side": "SELL",
                "type": "STOP",
                "quantity": 0.001,
                "price": 47000,
                "stop_price": 48000,
            }
        )
        assert req.order_type == OrderType.STOP
        assert req.price == 47000.0
        assert req.stop_price == 48000.0

    def test_stop_order_missing_price_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PlaceOrderRequest.model_validate(
                {
                    "symbol": "BTCUSDT",
                    "side": "SELL",
                    "type": "STOP",
                    "quantity": 0.001,
                    "stop_price": 48000,
                }
            )
        assert "price" in str(exc_info.value)

    def test_stop_order_missing_stop_price_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PlaceOrderRequest.model_validate(
                {
                    "symbol": "BTCUSDT",
                    "side": "SELL",
                    "type": "STOP",
                    "quantity": 0.001,
                    "price": 47000,
                }
            )
        assert "stop_price" in str(exc_info.value)

    def test_stop_order_missing_both_prices_raises(self):
        with pytest.raises(ValidationError):
            PlaceOrderRequest.model_validate(
                {"symbol": "BTCUSDT", "side": "SELL", "type": "STOP", "quantity": 0.001}
            )
