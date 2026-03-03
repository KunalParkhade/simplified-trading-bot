"""SQLAlchemy ORM models.

Each placed order is persisted as an ``Order`` row.  The table mirrors the
``OrderResponse`` schema so API responses can be built directly from ORM
instances using ``model_validate(order, from_attributes=True)``.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Order(Base):
    """Persisted record of a placed Binance Futures order."""

    __tablename__ = "orders"

    # Primary key — internal auto-increment, not the Binance orderId
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Binance fields
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    order_type: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    executed_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stop_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Metadata
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<Order id={self.id} order_id={self.order_id} "
            f"symbol={self.symbol} side={self.side} type={self.order_type} "
            f"status={self.status}>"
        )
