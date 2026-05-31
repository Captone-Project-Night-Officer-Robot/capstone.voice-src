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


class TranscriptEvent(BaseModel):
    robot_id: str = Field(..., description="Robot / room identifier")
    role: str = Field(..., description="'agent' | 'patient' | 'dispatch' | 'contact'")
    text: str
    final: bool = Field(default=True, description="False = interim STT, True = final")
    ts: float = Field(default=0.0)


class PatientEvent(BaseModel):
    robot_id: str
    patient_name: str = ""
    situation: str = ""
    pain_location: str = ""
    temperature: str = ""
    medical_conditions: str = ""
    medications: str = ""
    allergies: str = ""
    alcohol_consumed: str = ""
    notes: str = ""
    ts: float = Field(default=0.0)


class CallEvent(BaseModel):
    robot_id: str
    status: str = Field(
        ...,
        description="placing | ringing | active | ended | failed",
    )
    to: str = Field(default="", description="Destination phone number")
    room_name: str = ""
    detail: str = ""
    ts: float = Field(default=0.0)
