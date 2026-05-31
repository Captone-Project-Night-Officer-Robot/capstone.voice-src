"""
Best-effort push of live events from the agent worker to the dashboard API.

The worker runs as a separate process from the FastAPI app, so it ships
transcript lines, the patient record, and emergency-call status over loopback
HTTP to /api/v1/telemetry/*, which fans them out to /app over WebSocket.

Every call is fire-and-forget: a failed POST is logged at debug and never
interrupts the voice session.
"""

from __future__ import annotations

import os
import time

import httpx

from src.core.config import settings
from src.core.logging import logger

# Where the FastAPI app is reachable from the worker. Override with
# DASHBOARD_API_URL if the worker and API run on different hosts.
_API_BASE = os.environ.get(
    "DASHBOARD_API_URL",
    f"http://{settings.host if settings.host != '0.0.0.0' else 'localhost'}"
    f":{settings.port}",
)

_client = httpx.AsyncClient(timeout=2.0)


async def _post(path: str, payload: dict) -> None:
    try:
        await _client.post(f"{_API_BASE}/api/v1/telemetry/{path}", json=payload)
    except Exception as exc:  # never break the agent
        logger.debug(f"dashboard push {path} failed: {exc!r}")


async def push_transcript(
    robot_id: str, role: str, text: str, final: bool = True
) -> None:
    if not text.strip():
        return
    await _post(
        "transcript",
        {
            "robot_id": robot_id,
            "role": role,
            "text": text,
            "final": final,
            "ts": time.time(),
        },
    )


async def push_patient(robot_id: str, record: dict) -> None:
    await _post("patient", {"robot_id": robot_id, "ts": time.time(), **record})


async def push_call(
    robot_id: str,
    status: str,
    to: str = "",
    room_name: str = "",
    detail: str = "",
) -> None:
    await _post(
        "call",
        {
            "robot_id": robot_id,
            "status": status,
            "to": to,
            "room_name": room_name,
            "detail": detail,
            "ts": time.time(),
        },
    )
