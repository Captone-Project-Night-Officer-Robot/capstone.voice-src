"""
Patrol announcement audio.

The robot, while driving, plays a short bilingual safety message through its
speaker. To keep one voice across the whole system, the *speech itself* is
owned here (same ElevenLabs voice + model as the Night Officer agent) and the
Pi just fetches and plays the audio — exactly like it plays the agent's TTS
during a fall conversation.

    GET /api/v1/announce/patrol.wav   → 24 kHz mono WAV: EN phrase, a short
                                        gap, then the KR phrase. Rendered once
                                        via ElevenLabs and cached in memory.

Edit PATROL_PHRASES below to change the wording or add languages — the
multilingual model voices them all with the same speaker.
"""

from __future__ import annotations

import io
import wave

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import Response

from src.core.config import settings
from src.core.exceptions import NightOfficerError
from src.core.logging import logger

router = APIRouter(prefix="/announce", tags=["announce"])

# ElevenLabs pcm_24000 = raw 16-bit little-endian mono PCM at 24 kHz.
_SAMPLE_RATE = 24000
_GAP_SECONDS = 0.4  # silence inserted between phrases

# The patrol script. One ElevenLabs voice (settings.eleven_voice_id) +
# multilingual model speaks every line. Order is preserved in the output.
PATROL_PHRASES: list[str] = [
    "Safety robot patrolling. Please be careful.",
    "안전 로봇이 순찰 중입니다. 조심하세요.",
]

# Cached assembled WAV bytes — rendered on first request, reused after.
_cache: bytes | None = None


async def _tts_pcm(text: str) -> bytes:
    """Render one phrase to raw PCM via the ElevenLabs REST API."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.eleven_voice_id}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            params={"output_format": f"pcm_{_SAMPLE_RATE}"},
            headers={
                "xi-api-key": settings.eleven_api_key,
                "Content-Type": "application/json",
            },
            json={"text": text, "model_id": settings.eleven_tts_model},
        )
    resp.raise_for_status()
    return resp.content


async def _render_patrol_wav() -> bytes:
    """Render every phrase, join with gaps, wrap into a single WAV."""
    silence = b"\x00\x00" * int(_SAMPLE_RATE * _GAP_SECONDS)

    pcm_parts: list[bytes] = []
    for i, phrase in enumerate(PATROL_PHRASES):
        if i > 0:
            pcm_parts.append(silence)
        pcm_parts.append(await _tts_pcm(phrase))
    pcm = b"".join(pcm_parts)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm)
    return buf.getvalue()


@router.get("/patrol.wav", summary="Bilingual patrol announcement (WAV)")
async def patrol_wav(refresh: bool = Query(False, description="Force re-render")) -> Response:
    global _cache
    if _cache is None or refresh:
        try:
            _cache = await _render_patrol_wav()
            logger.info(
                "Rendered patrol announcement "
                f"({len(PATROL_PHRASES)} phrases, {len(_cache)} bytes)"
            )
        except Exception as exc:
            logger.error(f"Patrol TTS render failed: {exc!r}")
            raise NightOfficerError(
                "Could not render patrol announcement audio (ElevenLabs)."
            ) from exc
    return Response(content=_cache, media_type="audio/wav")
