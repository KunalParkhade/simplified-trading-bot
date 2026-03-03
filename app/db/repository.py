"""Repository pattern for Order persistence.

The repository layer decouples route handlers from SQLAlchemy so that:
* Route handlers never call ``session.execute`` directly.
* Tests can inject a fake/mock repository without touching a real DB.
* Changing the DB engine or query strategy only requires changes here.

Usage in a route handler::

    from app.dependencies import DBSessionDep
    from app.db.repository import OrderRepository

    async def place_order(session: DBSessionDep, ...):
        repo = OrderRepository(session)
        order = await repo.create(order_data)
"""

import logging
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order
from app.schemas.order import OrderResponse

logger = logging.getLogger(__name__)


class OrderRepository:
    """
    Data-access layer for :class:`~app.db.models.Order`.

    Args:
        session: An active ``AsyncSession`` provided by the DI layer.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, order_response: OrderResponse) -> Order:
        """
        Persist a new order record from a validated :class:`OrderResponse`.

        Args:
            order_response: The normalised response returned by the
                ``_parse_order_response`` helper in the orders route.

        Returns:
            The newly created and committed :class:`Order` ORM instance.
        """
        order = Order(
            order_id=order_response.order_id,
            symbol=order_response.symbol,
            side=order_response.side,
            order_type=order_response.order_type,
            status=order_response.status,
            executed_qty=order_response.executed_qty,
            avg_price=order_response.avg_price,
            stop_price=order_response.stop_price,
            timestamp=order_response.timestamp,
        )
        self._session.add(order)
        await self._session.commit()
        await self._session.refresh(order)
        logger.info(
            "Order persisted | db_id=%s binance_id=%s symbol=%s",
            order.id,
            order.order_id,
            order.symbol,
        )
        return order

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_by_id(self, db_id: int) -> Order | None:
        """Return an order by its internal DB primary key, or ``None``."""
        result = await self._session.execute(select(Order).where(Order.id == db_id))
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: int) -> Order | None:
        """Return an order by its Binance ``orderId``, or ``None``."""
        result = await self._session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def list_by_symbol(
        self, symbol: str, *, limit: int = 50, offset: int = 0
    ) -> Sequence[Order]:
        """
        Return a paginated list of orders for a given symbol.

        Args:
            symbol: Uppercase trading pair, e.g. ``BTCUSDT``.
            limit:  Maximum number of rows to return (default 50, max 100).
            offset: Number of rows to skip for pagination.
        """
        limit = min(limit, 100)
        result = await self._session.execute(
            select(Order)
            .where(Order.symbol == symbol.upper())
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def list_all(
        self, *, limit: int = 50, offset: int = 0
    ) -> Sequence[Order]:
        """
        Return a paginated list of all orders, newest first.

        Args:
            limit:  Maximum rows to return (default 50, max 100).
            offset: Rows to skip for pagination.
        """
        limit = min(limit, 100)
        result = await self._session.execute(
            select(Order)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
