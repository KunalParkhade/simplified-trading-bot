"""Async SQLAlchemy 2.x engine and session factory.

Design decisions
----------------
* **Single engine** created at module import time from the ``DATABASE_URL``
  setting.  The engine is cheap to hold; connections come from the pool.
* **AsyncSessionLocal** is a session factory used inside the
  ``get_db_session`` dependency.
* ``Base`` is the declarative base shared by every ORM model.

Database URLs:

  SQLite (dev/test):   ``sqlite+aiosqlite:///./trading_bot.db``
  PostgreSQL (prod):   ``postgresql+asyncpg://user:pass@host:5432/dbname``
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def build_engine(database_url: str) -> AsyncEngine:
    """
    Create and return an :class:`AsyncEngine` for the given URL.

    Args:
        database_url: SQLAlchemy-compatible async database URL.

    Notes:
        ``check_same_thread=False`` is required for SQLite in async mode.
        For PostgreSQL the kwarg is silently ignored by SQLAlchemy.
    """
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    return create_async_engine(
        database_url,
        connect_args=connect_args,
        echo=False,  # set to True to log all SQL for debugging
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return a session factory bound to *engine*."""
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
        class_=AsyncSession,
    )
