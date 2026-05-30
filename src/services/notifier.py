"""
Emergency dispatch via Twilio SMS.

The NightOfficerAgent calls `dispatch_emergency_alert()` from inside an LLM
tool once Step 5 of the screening flow is complete. We assemble the patient
record into a single SMS and send it to `settings.emergency_phone_number`.

Designed to never break the voice session: a Twilio failure is logged and
returned as `{"ok": False, ...}` so the agent can continue gracefully.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass

from src.core.config import settings
from src.core.logging import logger


# Twilio's SDK is sync, so we keep the import lazy + wrap the actual send
# in asyncio.to_thread() so it doesn't block the agent event loop.
_TWILIO_CLIENT = None  # set on first send


def _client():
    global _TWILIO_CLIENT
    if _TWILIO_CLIENT is None:
        # Import here so the dependency is optional until first send.
        from twilio.rest import Client  # type: ignore
        _TWILIO_CLIENT = Client(
            settings.twilio_account_sid,
            settings.twilio_auth_token,
        )
    return _TWILIO_CLIENT


@dataclass
class PatientRecord:
    patient_name: str = ""
    situation: str = ""
    pain_location: str = ""
    medical_conditions: str = ""
    medications: str = ""
    allergies: str = ""
    temperature: str = ""
    alcohol_consumed: str = ""
    notes: str = ""


def _format_sms(record: PatientRecord, robot_id: str | None) -> str:
    """One readable SMS body. Twilio segments long messages automatically."""
    lines = ["NIGHT OFFICER — EMERGENCY DISPATCH"]
    if robot_id:
        lines.append(f"Robot: {robot_id}")
    lines.append("")
    lines.append(f"Name: {record.patient_name or 'unknown'}")
    lines.append(f"Situation: {record.situation or 'not stated'}")
    lines.append(f"Pain: {record.pain_location or 'not stated'}")
    lines.append(f"Conditions: {record.medical_conditions or 'none stated'}")
    lines.append(f"Medications: {record.medications or 'none stated'}")
    lines.append(f"Allergies: {record.allergies or 'none stated'}")
    lines.append(f"Temperature: {record.temperature or 'unknown'}")
    lines.append(f"Alcohol: {record.alcohol_consumed or 'unknown'}")
    if record.notes:
        lines.append(f"Notes: {record.notes}")
    return "\n".join(lines)


async def dispatch_emergency_alert(
    record: PatientRecord,
    robot_id: str | None = None,
) -> dict:
    """Send the patient summary SMS. Returns {"ok": bool, ...}.

    Logs the payload either way — when Twilio is disabled (no creds in env)
    you'll still see the full record in the agent worker logs.
    """
    body = _format_sms(record, robot_id)
    logger.info(
        "Emergency dispatch payload\n%s",
        body,
        extra={"patient": asdict(record), "robot_id": robot_id},
    )

    if not settings.twilio_enabled:
        logger.warning(
            "Twilio not configured — SMS NOT sent. "
            "Set TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / "
            "TWILIO_FROM_NUMBER / EMERGENCY_PHONE_NUMBER in .env."
        )
        return {"ok": False, "reason": "twilio-disabled", "preview": body}

    def _send_sync() -> dict:
        try:
            msg = _client().messages.create(
                from_=settings.twilio_from_number,
                to=settings.emergency_phone_number,
                body=body,
            )
            return {"ok": True, "sid": msg.sid}
        except Exception as exc:
            logger.exception("Twilio SMS send failed")
            return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}

    return await asyncio.to_thread(_send_sync)
