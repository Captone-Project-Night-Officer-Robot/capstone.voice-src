from __future__ import annotations

from pydantic import BaseModel, Field


class SessionStartRequest(BaseModel):
    robot_id: str = Field(..., description="Unique robot identifier, e.g. 'robot-01'")
    room_name: str | None = Field(
        default=None,
        description="Optional room name. Auto-generated from robot_id if omitted.",
    )


class SessionStartResponse(BaseModel):
    room_name: str
    token: str
    livekit_url: str


class SessionStatusResponse(BaseModel):
    status: str = "ok"
    room_name: str