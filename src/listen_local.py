"""
Laptop-side audio listener for the Night Officer voice agent.

The car (Pi) has no speaker, so this script subscribes to whatever LiveKit
room is currently active and plays the agent's TTS audio through the laptop's
default output device. Stays alive across multiple sessions — when one room
ends, it just keeps polling for the next.

Run on the laptop, in its own terminal, alongside `src.main` and `src.worker`:

    python -m src.listen_local

Prerequisites:
    macOS:  brew install portaudio  &&  pip install sounddevice
    Linux:  sudo apt install libportaudio2  &&  pip install sounddevice

Requires a valid .env with LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET.
The listener mints its own subscribe-only token (no can_publish).
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import timedelta

import httpx
import numpy as np

try:
    import sounddevice as sd  # type: ignore
except Exception as exc:
    sys.stderr.write(
        f"[listen] sounddevice import failed: {exc}\n"
        "    macOS:  brew install portaudio  &&  pip install sounddevice\n"
        "    Linux:  sudo apt install libportaudio2  &&  pip install sounddevice\n"
    )
    sys.exit(1)

from dotenv import load_dotenv
from livekit import rtc
from livekit.api import AccessToken, VideoGrants

load_dotenv()

API_URL = os.environ.get("VOICE_API_URL", "http://localhost:8001")
POLL_INTERVAL = 2.0
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "").strip()
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "").strip()
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "").strip()


def _check_env() -> None:
    missing = [
        k for k in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
        if not os.environ.get(k, "").strip()
    ]
    if missing:
        sys.stderr.write(
            "[listen] missing env vars: " + ", ".join(missing) + "\n"
            "       make sure .env is in the project root.\n"
        )
        sys.exit(1)


def _make_listener_token(room_name: str) -> str:
    return (
        AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
        .with_identity(f"laptop-listener-{os.getpid()}")
        .with_name("laptop-listener")
        .with_ttl(timedelta(hours=2))
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
                can_subscribe=True,
                can_publish=False,
            )
        )
        .to_jwt()
    )


class RoomListener:
    """Joins one room, plays incoming audio, exits when the room ends."""

    def __init__(self, room_name: str) -> None:
        self.room_name = room_name
        self.room = rtc.Room()
        self._stream: "sd.OutputStream | None" = None
        self._stream_lock = asyncio.Lock()
        self._disconnected = asyncio.Event()

    async def run(self) -> None:
        @self.room.on("track_subscribed")
        def _on_subscribed(track, publication, participant):  # noqa: ARG001
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                print(
                    f"[listen] audio track from {participant.identity} "
                    f"in {self.room_name}"
                )
                asyncio.create_task(self._consume_audio(track))

        @self.room.on("disconnected")
        def _on_disconnected(*_a):
            print(f"[listen] room disconnected: {self.room_name}")
            self._disconnected.set()

        @self.room.on("participant_disconnected")
        def _on_participant_disconnected(participant):
            print(
                f"[listen] participant left {self.room_name}: {participant.identity}"
            )

        token = _make_listener_token(self.room_name)
        try:
            await self.room.connect(LIVEKIT_URL, token)
            print(f"[listen] joined {self.room_name}")
        except Exception as exc:
            print(f"[listen] connect failed for {self.room_name}: {exc}")
            return

        try:
            await self._disconnected.wait()
        finally:
            await self._cleanup()

    async def _consume_audio(self, track) -> None:
        try:
            stream = rtc.AudioStream(track)
            async for ev in stream:
                frame = ev.frame
                if frame is None:
                    continue

                samples = np.frombuffer(frame.data, dtype=np.int16)
                channels = max(1, frame.num_channels)

                async with self._stream_lock:
                    if self._stream is None:
                        self._stream = sd.OutputStream(
                            samplerate=frame.sample_rate,
                            channels=channels,
                            dtype="int16",
                        )
                        self._stream.start()
                        print(
                            f"[listen] output stream started "
                            f"{frame.sample_rate}Hz x{channels}ch "
                            f"({self.room_name})"
                        )

                if channels > 1:
                    samples = samples.reshape(-1, channels)
                self._stream.write(samples)
        except Exception as exc:
            print(f"[listen] audio task error in {self.room_name}: {exc}")

    async def _cleanup(self) -> None:
        try:
            await self.room.disconnect()
        except Exception:
            pass
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None


async def main() -> None:
    _check_env()

    print(f"[listen] LiveKit URL : {LIVEKIT_URL}")
    print(f"[listen] Voice API   : {API_URL}")
    print(f"[listen] Polling every {POLL_INTERVAL}s for new rooms")

    joined: dict[str, asyncio.Task] = {}

    async with httpx.AsyncClient(base_url=API_URL) as client:
        while True:
            try:
                resp = await client.get("/api/v1/session/active", timeout=2.0)
                resp.raise_for_status()
                sessions = resp.json().get("sessions", [])
            except Exception as exc:
                print(f"[listen] poll error: {exc}")
                await asyncio.sleep(POLL_INTERVAL)
                continue

            current = {s["room_name"] for s in sessions}

            for room_name in current - joined.keys():
                print(f"[listen] new room discovered: {room_name}")
                listener = RoomListener(room_name)
                joined[room_name] = asyncio.create_task(listener.run())

            # GC finished listeners.
            for room_name in [r for r, t in joined.items() if t.done()]:
                del joined[room_name]
                print(f"[listen] room {room_name} cleaned up")

            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[listen] stopped.")
