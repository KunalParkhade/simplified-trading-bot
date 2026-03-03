"""FastAPI dependency providers.

Import the ``Annotated`` aliases in route handlers to get fully-typed,
injected dependencies via ``Depends()``.

Example::

    @router.post("/orders")
    async def place_order(body: ..., client: BinanceClientDep, session: DBSessionDep) -> ...:
        ...
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.services.binance_client import BinanceClient

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

SettingsDep = Annotated[Settings, Depends(get_settings)]


# ---------------------------------------------------------------------------
# Binance client
# ---------------------------------------------------------------------------

def get_binance_client(request: Request, settings: SettingsDep) -> BinanceClient:
    """
    Provide a :class:`BinanceClient` backed by the shared ``httpx.AsyncClient``
    stored in ``app.state`` (initialised during the app lifespan).

    Raises HTTP **503** if Binance credentials are not configured, so callers
    receive a clean error instead of an unhandled ``ValueError``.
    """
    if not settings.binance_api_key or not settings.binance_api_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Binance API credentials are not configured. "
                "Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables."
            ),
        )
    return BinanceClient(
        api_key=settings.binance_api_key,
        api_secret=settings.binance_api_secret,
        base_url=settings.binance_base_url,
        http_client=request.app.state.http_client,
    )


BinanceClientDep = Annotated[BinanceClient, Depends(get_binance_client)]


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------

async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an :class:`AsyncSession` from the session factory stored in
    ``app.state.db_session_factory`` (initialised during the app lifespan).

    The session is automatically closed after the request completes.
    Rollback on exception is handled by SQLAlchemy's context manager.
    """
    async with request.app.state.db_session_factory() as session:
        yield session


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
