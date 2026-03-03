"""Alembic environment — async-compatible (SQLAlchemy 2.x + asyncio).

This env.py:
* Reads the database URL from the ``DATABASE_URL`` env/settings, falling
  back to the ``sqlalchemy.url`` value in ``alembic.ini``.
* Imports all ORM models so autogenerate can detect schema changes.
* Uses ``AsyncEngine`` + ``run_sync`` for online migrations.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---- Import all models so autogenerate can detect them ----
from app.db.base import Base  # noqa: F401 — registers Base.metadata
import app.db.models  # noqa: F401 — side-effect: registers Order model

# Alembic Config object
config = context.config

# Override sqlalchemy.url from Settings if available
try:
    from app.config import get_settings
    _db_url = get_settings().database_url
    if _db_url:
        config.set_main_option("sqlalchemy.url", _db_url)
except Exception:
    pass  # Fall back to alembic.ini value

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL scripts)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations via run_sync."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in online mode using an async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
