"""
Place an outbound emergency phone call via LiveKit SIP.

Creates a fresh room (carrying the PatientRecord in its metadata), then dials
the emergency contact into it through the LiveKit outbound trunk. The worker's
agent dispatch spins up an EmergencyDispatchAgent for that room (routed by the
`emergency-` room-name prefix in src/agent/session.py), which talks to whoever
answers.

Talks only to LiveKit (not the local API), so it works the same whether it is
called from the worker process (NightOfficer on_exit) or the API process
(POST /api/v1/emergency/call manual test).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict

from livekit import api

from src.client.dashboard import push_call
from src.core.config import settings
from src.core.logging import logger
from src.services.notifier import PatientRecord

EMERGENCY_ROOM_PREFIX = "emergency-"


def _lkapi() -> api.LiveKitAPI:
    # Explicit creds so it works in the worker process too (where .env isn't
    # necessarily exported into os.environ).
    return api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )


async def place_emergency_call(
    record: PatientRecord,
    robot_id: str | None = None,
) -> dict:
    """Dial the emergency contact and hand off the patient record.

    Returns {"ok": bool, ...}. Never raises — a failure is logged and returned
    so the caller (agent on_exit / API) keeps running.
    """
    logger.info(
        "Emergency call requested",
        extra={"robot_id": robot_id, "patient": asdict(record)},
    )

    rid = robot_id or "robot"

    if not settings.emergency_call_ready:
        logger.warning(
            "Emergency call not configured — NOT calling. Set "
            "LIVEKIT_SIP_OUTBOUND_TRUNK_ID, EMERGENCY_PHONE_NUMBER, and "
            "EMERGENCY_CALL_ENABLED in .env."
        )
        await push_call(rid, "failed", detail="not configured")
        return {"ok": False, "reason": "not-configured"}

    room_name = f"{EMERGENCY_ROOM_PREFIX}{rid}-{uuid.uuid4().hex[:8]}"
    metadata = json.dumps({"record": asdict(record), "robot_id": robot_id})
    await push_call(
        rid, "placing", to=settings.emergency_phone_number, room_name=room_name
    )

    lkapi = _lkapi()
    try:
        # Create the room WITH the record in metadata first, so the dispatched
        # agent can read it before greeting.
        await lkapi.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                metadata=metadata,
                empty_timeout=120,  # tear down if nobody ever answers
            )
        )

        # Dial the contact into that room. Returns once dialing starts (the
        # agent waits for the call to be answered before speaking).
        await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=settings.livekit_sip_outbound_trunk_id,
                sip_call_to=settings.emergency_phone_number,
                room_name=room_name,
                participant_identity="emergency-callee",
                participant_name="Emergency Contact",
            )
        )
        logger.info(
            "Emergency call placed",
            extra={"room": room_name, "to": settings.emergency_phone_number},
        )
        return {"ok": True, "room_name": room_name}
    except Exception as exc:
        logger.exception("Emergency call failed")
        await push_call(rid, "failed", room_name=room_name, detail=type(exc).__name__)
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}
    finally:
        await lkapi.aclose()
