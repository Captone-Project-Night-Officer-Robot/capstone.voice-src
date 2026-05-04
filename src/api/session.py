from __future__ import annotations

from fastapi import APIRouter

from src.client.livekit import create_room_token, generate_room_name
from src.core.config import settings
from src.core.logging import logger
from src.models.session import SessionStartRequest, SessionStartResponse

router = APIRouter(prefix="/session", tags=["session"])


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

    return SessionStartResponse(
        room_name=room_name,
        token=token,
        livekit_url=settings.livekit_url,
    )