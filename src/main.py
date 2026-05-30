from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api import api_router
from src.api.telemetry import loguru_broadcast_sink, set_log_loop
from src.core.config import settings
from src.core.errors import domain_exception_handler, unhandled_exception_handler
from src.core.exceptions import NightOfficerError
from src.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Bridge loguru → dashboard WebSocket. enqueue=True moves the sink call
    # to a background thread so a slow subscriber can't stall handlers.
    set_log_loop(asyncio.get_running_loop())
    sink_id = logger.add(
        loguru_broadcast_sink,
        level=settings.log_level,
        enqueue=True,
    )
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    try:
        yield
    finally:
        logger.info(f"Shutting down {settings.app_name}")
        logger.remove(sink_id)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(NightOfficerError, domain_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(api_router, prefix="/api/v1")


# ── Robot map dashboard ──────────────────────────────────────────────────────
# Static file lives next to the project root in `static/dashboard.html`. The
# dashboard subscribes to /api/v1/telemetry/ws and renders the path + fall pins.

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/dashboard", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(_STATIC_DIR / "dashboard.html")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


def run() -> None:
    """Run the API bound to settings.host/settings.port.

    Use this so the server is reachable from the Pi (binds 0.0.0.0 by default)
    instead of having to remember the uvicorn CLI flags.
    """
    import uvicorn

    logger.info(
        f"Starting API on http://{settings.host}:{settings.port}"
        f" (docs at /docs, health at /api/v1/health)"
    )
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()