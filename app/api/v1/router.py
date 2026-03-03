"""API v1 — aggregate router.

All v1 sub-routers are registered here and mounted under ``/api/v1``
in :mod:`app.main`.
"""

from fastapi import APIRouter

from app.api.v1 import orders

api_v1_router = APIRouter()
api_v1_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
