from __future__ import annotations

from livekit.agents import AgentSession, JobContext, RoomInputOptions, TurnHandlingOptions
from livekit.plugins import elevenlabs, noise_cancellation, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from src.agent.night_officer import NightOfficerAgent
from src.core.config import settings
from src.core.logging import logger


async def start_agent_session(ctx: JobContext) -> None:
    """Build and start the AgentSession. All config from Settings."""
    logger.info("Connecting to room", extra={"room": ctx.room.name})

    await ctx.connect()

    session = AgentSession(
        # VAD — tuned thresholds to reduce false triggers from background noise
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
        # Turn handling — groups all turn/interruption config, fixes deprecation warning
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
            min_endpointing_delay=settings.agent_min_endpointing_delay,
            max_endpointing_delay=settings.agent_max_endpointing_delay,
            allow_interruptions=settings.agent_allow_interruptions,
        ),
    )

    # Room names are minted as `{robot_id}-{uuid8}` in client/livekit.py, so
    # everything before the final hyphen segment is the robot id.
    robot_id = (
        ctx.room.name.rsplit("-", 1)[0] if "-" in ctx.room.name else ctx.room.name
    )

    await session.start(
        room=ctx.room,
        agent=NightOfficerAgent(robot_id=robot_id),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    logger.info("AgentSession started", extra={"room": ctx.room.name})