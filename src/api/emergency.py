"""
Manual trigger for the outbound emergency call.

Lets you place the call (and exercise the EmergencyDispatchAgent) without the
robot or a full NightOfficer conversation — handy for testing the phone leg in
isolation:

    curl -X POST http://localhost:8001/api/v1/emergency/call \
        -H "Content-Type: application/json" \
        -d '{"patient_name": "Test Patient", "situation": "fell in the hallway",
             "pain_location": "left hip", "robot_id": "raspbot-01"}'

In production the same call is placed automatically by the NightOfficerAgent
when its conversation ends (see src/agent/night_officer.py on_exit).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from src.core.logging import logger
from src.services.emergency_call import place_emergency_call
from src.services.notifier import PatientRecord

router = APIRouter(prefix="/emergency", tags=["emergency"])


class EmergencyCallRequest(BaseModel):
    patient_name: str = ""
    situation: str = ""
    pain_location: str = ""
    medical_conditions: str = ""
    medications: str = ""
    allergies: str = ""
    temperature: str = ""
    alcohol_consumed: str = ""
    notes: str = ""
    robot_id: str | None = None


@router.post("/call", summary="Place an outbound emergency call")
async def emergency_call(body: EmergencyCallRequest) -> dict:
    record = PatientRecord(
        patient_name=body.patient_name,
        situation=body.situation,
        pain_location=body.pain_location,
        medical_conditions=body.medical_conditions,
        medications=body.medications,
        allergies=body.allergies,
        temperature=body.temperature,
        alcohol_consumed=body.alcohol_consumed,
        notes=body.notes,
    )
    logger.info("Manual emergency call trigger", extra={"robot_id": body.robot_id})
    return await place_emergency_call(record, robot_id=body.robot_id)
