from __future__ import annotations

import uuid
from datetime import timedelta

from livekit.api import AccessToken, VideoGrants

from src.core.config import settings
from src.core.exceptions import LiveKitTokenError
from src.core.logging import logger


async def create_room_token(robot_id: str, room_name: str) -> str:
    """Mint a signed LiveKit JWT for the robot to join a room."""
    try:
        token = (
            AccessToken(
                api_key=settings.livekit_api_key,
                api_secret=settings.livekit_api_secret,
            )
            .with_identity(robot_id)
            .with_name(robot_id)
            .with_ttl(timedelta(hours=1))
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            .to_jwt()
        )
        logger.info(
            "LiveKit token created",
            extra={"robot_id": robot_id, "room": room_name},
        )
        return token
    except Exception as exc:
        raise LiveKitTokenError(f"Token generation failed: {exc}") from exc


def generate_room_name(robot_id: str) -> str:
    return f"{robot_id}-{str(uuid.uuid4())[:8]}"