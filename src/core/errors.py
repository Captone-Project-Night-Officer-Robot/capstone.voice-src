from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from src.core.exceptions import LiveKitTokenError, NightOfficerError
from src.core.logging import logger


async def domain_exception_handler(
    request: Request, exc: NightOfficerError
) -> JSONResponse:
    status = 502 if isinstance(exc, LiveKitTokenError) else 500
    logger.error(f"Domain error [{type(exc).__name__}]: {exc} — path: {request.url.path}")
    return JSONResponse(
        status_code=status,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(f"Unhandled exception at {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )