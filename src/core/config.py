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
    eleven_tts_model: str = "eleven_multilingual_v2"
    eleven_voice_id: str = Field(..., alias="ELEVEN_VOICE_ID")
    eleven_stt_model: str = "scribe_v2_realtime"
    eleven_stt_language: str = "en"

    # ── Agent tuning ──────────────────────────────────────────────────────────
    agent_min_endpointing_delay: float = 1.2
    agent_max_endpointing_delay: float = 8.0
    agent_allow_interruptions: bool = True

    # ── VAD tuning ────────────────────────────────────────────────────────────
    vad_activation_threshold: float = 0.6      # higher = less sensitive to noise
    vad_min_silence_duration: float = 0.3      # seconds of silence before speech ends
    vad_min_speech_duration: float = 0.1       # minimum speech duration to count

    # ── Twilio (emergency SMS dispatch) ───────────────────────────────────────
    # When all four are populated, the NightOfficerAgent gains a
    # `dispatch_emergency` LLM tool that texts collected patient info to the
    # emergency contact at Step 6 of the screening flow. Leaving any of these
    # blank disables the tool gracefully — the agent still completes the
    # conversation, dispatch is just logged instead of sent.
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(default="", alias="TWILIO_FROM_NUMBER")
    emergency_phone_number: str = Field(default="", alias="EMERGENCY_PHONE_NUMBER")

    @property
    def twilio_enabled(self) -> bool:
        return bool(
            self.twilio_account_sid
            and self.twilio_auth_token
            and self.twilio_from_number
            and self.emergency_phone_number
        )


settings = Settings()