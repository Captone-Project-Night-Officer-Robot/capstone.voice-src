from __future__ import annotations

from livekit.agents import AgentSession, JobContext
from livekit.plugins import elevenlabs, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from src.agent.night_officer import NightOfficerAgent
from src.core.config import settings
from src.core.logging import logger


async def start_agent_session(ctx: JobContext) -> None:
    """Build and start the AgentSession. All config from Settings."""
    logger.info("Connecting to room", extra={"room": ctx.room.name})
    await ctx.connect()

    session = AgentSession(
        vad=silero.VAD.load(),
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
        turn_detection=MultilingualModel(),
        min_endpointing_delay=settings.agent_min_endpointing_delay,
        max_endpointing_delay=settings.agent_max_endpointing_delay,
        allow_interruptions=settings.agent_allow_interruptions,
    )

    await session.start(room=ctx.room, agent=NightOfficerAgent())
    logger.info("AgentSession started", extra={"room": ctx.room.name})