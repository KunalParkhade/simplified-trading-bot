"""FastAPI exception handlers.

All handlers produce a consistent JSON error envelope::

    {
        "error": "<machine-readable-code>",
        "detail": "<human-readable detail or list of validation errors>"
    }

Register all handlers by calling :func:`register_exception_handlers` on
the FastAPI application instance.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import BinanceAPIError, OrderNotFoundError, OrderValidationError

logger = logging.getLogger(__name__)


def _error_body(error: str, detail: str | list) -> dict:
    return {"error": error, "detail": detail}


async def _binance_error_handler(request: Request, exc: BinanceAPIError) -> JSONResponse:
    logger.warning(
        "Binance API error | path=%s code=%s message=%s",
        request.url.path,
        exc.code,
        exc.message,
    )
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=_error_body("binance_api_error", f"[{exc.code}] {exc.message}"),
    )


async def _order_validation_error_handler(
    request: Request, exc: OrderValidationError
) -> JSONResponse:
    logger.warning("Order validation error | path=%s error=%s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body("order_validation_error", str(exc)),
    )


async def _order_not_found_handler(
    request: Request, exc: OrderNotFoundError
) -> JSONResponse:
    logger.info("Order not found | path=%s error=%s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=_error_body("order_not_found", str(exc)),
    )


async def _request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Override FastAPI's default 422 to use the consistent error envelope."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body("validation_error", jsonable_encoder(exc.errors())),
    )


async def _pydantic_validation_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """
    Catch raw ``pydantic.ValidationError`` that escapes FastAPI's body-parsing
    conversion (e.g. ``model_validator(mode='after')`` errors).
    ``jsonable_encoder`` is used to safely serialise the ``ctx`` field which
    may contain non-JSON-serialisable Python objects such as ``ValueError``.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body("validation_error", jsonable_encoder(exc.errors())),
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled error | method=%s path=%s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("internal_server_error", "An unexpected error occurred."),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to a FastAPI application."""
    app.add_exception_handler(BinanceAPIError, _binance_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(OrderValidationError, _order_validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(OrderNotFoundError, _order_not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _request_validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(PydanticValidationError, _pydantic_validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_error_handler)  # type: ignore[arg-type]
