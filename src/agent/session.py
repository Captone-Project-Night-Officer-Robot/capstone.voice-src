from __future__ import annotations

import asyncio
import json
import time
from dataclasses import fields

from livekit.agents import AgentSession, JobContext, RoomInputOptions, TurnHandlingOptions
from livekit.plugins import elevenlabs, noise_cancellation, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from src.agent.emergency_dispatch import EmergencyDispatchAgent
from src.agent.night_officer import NightOfficerAgent
from src.client.dashboard import push_call, push_transcript
from src.core.config import settings
from src.core.logging import logger
from src.services.emergency_call import EMERGENCY_ROOM_PREFIX
from src.services.notifier import PatientRecord


def _build_session() -> AgentSession:
    """Shared VAD/STT/LLM/TTS pipeline used by both agents."""
    return AgentSession(
        vad=silero.VAD.load(
            activation_threshold=settings.vad_activation_threshold,
            min_silence_duration=settings.vad_min_silence_duration,
            min_speech_duration=settings.vad_min_speech_duration,
        ),
        stt=elevenlabs.STT(
            model_id=settings.eleven_stt_model,
            language_code=settings.eleven_stt_language,
            api_key=settings.eleven_api_key,
        ),
        llm=openai.LLM(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=settings.groq_temperature,
        ),
        tts=elevenlabs.TTS(
            model=settings.eleven_tts_model,
            voice_id=settings.eleven_voice_id,
            auto_mode=True,
            api_key=settings.eleven_api_key,
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
            min_endpointing_delay=settings.agent_min_endpointing_delay,
            max_endpointing_delay=settings.agent_max_endpointing_delay,
            allow_interruptions=settings.agent_allow_interruptions,
        ),
    )


def _wire_transcript(session: AgentSession, robot_id: str, agent_role: str,
                     human_role: str) -> None:
    """Stream the conversation to the dashboard.

    `agent_role`/`human_role` label the two sides for the UI, e.g.
    ("agent", "patient") for NightOfficer or ("dispatch", "contact") for the
    emergency call.
    """

    @session.on("conversation_item_added")
    def _on_item(ev) -> None:  # noqa: ANN001
        item = getattr(ev, "item", None)
        if item is None:
            return
        text = (getattr(item, "text_content", "") or "").strip()
        if not text:
            return
        role = agent_role if getattr(item, "role", "") == "assistant" else human_role
        asyncio.create_task(push_transcript(robot_id, role, text, final=True))

    @session.on("user_input_transcribed")
    def _on_user(ev) -> None:  # noqa: ANN001
        # Interim STT — show the human side updating live; finals arrive via
        # conversation_item_added above.
        if getattr(ev, "is_final", False):
            return
        text = (getattr(ev, "transcript", "") or "").strip()
        if text:
            asyncio.create_task(push_transcript(robot_id, human_role, text, final=False))


def _robot_id_from_room(room_name: str) -> str:
    # Room names are minted as `{prefix?}{robot_id}-{uuid8}`; strip the uuid.
    base = room_name[len(EMERGENCY_ROOM_PREFIX):] if room_name.startswith(
        EMERGENCY_ROOM_PREFIX
    ) else room_name
    return base.rsplit("-", 1)[0] if "-" in base else base


async def start_agent_session(ctx: JobContext) -> None:
    """Single entrypoint for both agents — routed by room name.

    `emergency-*` rooms run the EmergencyDispatchAgent (outbound phone call);
    everything else runs the NightOfficerAgent (the robot conversation).
    """
    logger.info("Connecting to room", extra={"room": ctx.room.name})
    await ctx.connect()

    if ctx.room.name.startswith(EMERGENCY_ROOM_PREFIX):
        await _run_emergency(ctx)
    else:
        await _run_night_officer(ctx)


async def _run_night_officer(ctx: JobContext) -> None:
    session = _build_session()
    robot_id = _robot_id_from_room(ctx.room.name)
    _wire_transcript(session, robot_id, agent_role="agent", human_role="patient")
    # The emergency phone call is placed from inside the dispatch_emergency
    # tool at Step 3 (see night_officer.py), so the call goes out the instant
    # the agent says "I am calling one one nine" — no shutdown hook needed.
    await session.start(
        room=ctx.room,
        agent=NightOfficerAgent(robot_id=robot_id),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    logger.info("NightOfficer session started", extra={"room": ctx.room.name})


async def _run_emergency(ctx: JobContext) -> None:
    record, robot_id = _parse_room_metadata(ctx.room.metadata)
    logger.info(
        "Emergency call room — waiting for the contact to answer",
        extra={"room": ctx.room.name, "robot_id": robot_id},
    )

    rid = robot_id or "robot"

    # The SIP participant joins while ringing; wait until it's actually
    # answered so the agent doesn't greet a ringing line.
    participant = await ctx.wait_for_participant()
    await push_call(rid, "ringing", room_name=ctx.room.name)
    answered = await _wait_until_answered(participant)
    await push_call(rid, "active" if answered else "ringing", room_name=ctx.room.name)

    session = _build_session()
    _wire_transcript(session, rid, agent_role="dispatch", human_role="contact")

    # Mark the call ended when the room shuts down.
    async def _on_shutdown(*_a) -> None:
        await push_call(rid, "ended", room_name=ctx.room.name)

    ctx.add_shutdown_callback(_on_shutdown)

    await session.start(
        room=ctx.room,
        agent=EmergencyDispatchAgent(record=record, robot_id=robot_id),
        # BVCTelephony is tuned for 8 kHz phone audio.
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )
    logger.info("EmergencyDispatch session started", extra={"room": ctx.room.name})


async def _wait_until_answered(participant, timeout: float = 45.0) -> bool:
    """Poll the SIP participant until the call is answered (or timeout)."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        status = (participant.attributes or {}).get("sip.callStatus")
        if status == "active":
            return True
        # Answered calls publish an audio track — treat that as connected too.
        if participant.track_publications:
            return True
        await asyncio.sleep(0.3)
    logger.warning("SIP call not confirmed answered within timeout — proceeding")
    return False


def _parse_room_metadata(metadata: str) -> tuple[PatientRecord, str | None]:
    try:
        data = json.loads(metadata) if metadata else {}
    except Exception:
        data = {}
    rec = data.get("record", {}) or {}
    valid = {f.name for f in fields(PatientRecord)}
    record = PatientRecord(**{k: v for k, v in rec.items() if k in valid})
    return record, data.get("robot_id")
