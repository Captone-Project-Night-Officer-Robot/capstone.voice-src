from __future__ import annotations

import time
from threading import Lock
from typing import Any

from fastapi import APIRouter

from src.client.livekit import create_room_token, generate_room_name
from src.core.config import settings
from src.core.logging import logger
from src.models.session import SessionStartRequest, SessionStartResponse

router = APIRouter(prefix="/session", tags=["session"])


# In-memory active-session registry. Listeners (e.g. listen_local.py on the
# laptop) poll /active to discover new rooms and join them as subscribers.
# Sessions older than this TTL are dropped on every /active request.
_ACTIVE_TTL_SECONDS = 30 * 60
_active: dict[str, dict[str, Any]] = {}
_active_lock = Lock()


def _record_active(room_name: str, robot_id: str) -> None:
    with _active_lock:
        _active[room_name] = {
            "room_name": room_name,
            "robot_id": robot_id,
            "started_at": time.time(),
        }


def _list_active() -> list[dict]:
    with _active_lock:
        cutoff = time.time() - _ACTIVE_TTL_SECONDS
        for k in [k for k, v in _active.items() if v["started_at"] < cutoff]:
            del _active[k]
        return list(_active.values())


def _remove_active(room_name: str) -> None:
    with _active_lock:
        _active.pop(room_name, None)


@router.post(
    "/start",
    response_model=SessionStartResponse,
    summary="Start a voice triage session",
    description=(
        "Called by the robot FSM when entering TRIAGE state. "
        "Returns a signed LiveKit token so the robot can join the room."
    ),
)
async def start_session(body: SessionStartRequest) -> SessionStartResponse:
    room_name = body.room_name or generate_room_name(body.robot_id)

    logger.info(
        "Starting session",
        extra={"robot_id": body.robot_id, "room_name": room_name},
    )

    token = await create_room_token(robot_id=body.robot_id, room_name=room_name)
    _record_active(room_name, body.robot_id)

    return SessionStartResponse(
        room_name=room_name,
        token=token,
        livekit_url=settings.livekit_url,
    )


@router.get(
    "/active",
    summary="List currently active voice sessions",
    description="Used by laptop-side listeners (e.g. listen_local.py) to "
    "auto-join newly created rooms and play TTS audio locally.",
)
async def list_active_sessions() -> dict:
    return {"sessions": _list_active()}


@router.delete(
    "/active/{room_name}",
    summary="Drop a session from the active registry",
)
async def remove_active(room_name: str) -> dict:
    _remove_active(room_name)
    return {"ok": True, "room_name": room_name}