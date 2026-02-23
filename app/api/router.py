from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import extract, health, search

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(extract.router, tags=["extract"])
