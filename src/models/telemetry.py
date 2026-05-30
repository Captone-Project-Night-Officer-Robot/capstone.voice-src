from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PoseUpdate(BaseModel):
    robot_id: str = Field(..., description="Unique robot identifier")
    x: float = Field(..., description="Pose x in meters (start frame)")
    y: float = Field(..., description="Pose y in meters (start frame)")
    theta: float = Field(..., description="Heading in radians, +ccw from +x")
    state: str = Field(..., description="FSM state name (follow/search/...)")
    ts: float = Field(..., description="Robot wall-clock timestamp (seconds)")
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Free-form telemetry sidecar. Currently: main_fps, fall_fps, "
            "fall_infer_ms, people, tracked_falling_ids."
        ),
    )


class FallEvent(BaseModel):
    robot_id: str
    x: float
    y: float
    ts: float
    track_id: int | None = Field(
        default=None,
        description="YOLO track id of the person who triggered the pin.",
    )


class LogEvent(BaseModel):
    source: str = Field(..., description="Originator: 'api', 'worker', or '<robot_id>'.")
    level: str = Field(..., description="DEBUG | INFO | WARNING | ERROR")
    message: str
    ts: float
    function: str = ""
