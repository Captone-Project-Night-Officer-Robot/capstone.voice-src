from fastapi import APIRouter

from src.api.health import router as health_router
from src.api.session import router as session_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(session_router)

__all__ = ["api_router"]