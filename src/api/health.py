from __future__ import annotations

from fastapi import APIRouter

from src.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }