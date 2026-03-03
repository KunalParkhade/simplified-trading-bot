"""FastAPI application factory.

Entry point for the trading bot REST API.  Start with::

    uvicorn app.main:app --reload

The ``lifespan`` context manager handles startup / shutdown:

* **Startup** — creates a single ``httpx.AsyncClient`` stored in
  ``app.state.http_client`` for connection-pool reuse across all requests.
* **Shutdown** — gracefully closes the HTTP client.
"""

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.config import Settings, get_settings
from app.core.handlers import register_exception_handlers

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application-level resources across the process lifetime."""
    settings: Settings = get_settings()

    # Configure root logging based on settings
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create a single shared async HTTP client (connection pooling)
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
    )
    app.state.http_client = http_client
    logger.info(
        "Startup complete | app=%s version=%s",
        settings.app_name,
        settings.app_version,
    )

    yield  # ← application runs here

    await http_client.aclose()
    logger.info("HTTP client closed — shutdown complete.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "**Binance Futures Testnet** trading bot — REST API.\n\n"
            "Supports MARKET, LIMIT, and STOP-LIMIT order placement "
            "with full async request handling and structured error responses."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Exception handlers ---
    register_exception_handlers(app)

    # --- Versioned routers ---
    app.include_router(api_v1_router, prefix="/api/v1")

    # --- Health / readiness probe ---
    @app.get("/health", tags=["Health"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        """Returns 200 OK when the service is running."""
        return {"status": "ok", "version": settings.app_version}

    return app


# Module-level app instance consumed by uvicorn
app = create_app()
