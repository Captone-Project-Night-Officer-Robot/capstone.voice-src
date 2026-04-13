from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "Night Officer Voice Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # ── LiveKit ───────────────────────────────────────────────────────────────
    livekit_url: str = Field(..., alias="LIVEKIT_URL")
    livekit_api_key: str = Field(..., alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(..., alias="LIVEKIT_API_SECRET")

    # ── Groq ─────────────────────────────────────────────────────────────────
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")
    groq_model: str = "llama-3.3-70b-versatile"
    groq_max_tokens: int = 120
    groq_temperature: float = 0.3

    # ── ElevenLabs ────────────────────────────────────────────────────────────
    eleven_api_key: str = Field(..., alias="ELEVEN_API_KEY")
    eleven_tts_model: str = "eleven_flash_v2_5"
    eleven_voice_id: str = Field(..., alias="ELEVEN_VOICE_ID")
    eleven_stt_model: str = "scribe_v2_realtime"
    eleven_stt_language: str = "en"

    # ── Agent tuning ──────────────────────────────────────────────────────────
    agent_min_endpointing_delay: float = 1.2
    agent_max_endpointing_delay: float = 8.0
    agent_allow_interruptions: bool = True


settings = Settings()