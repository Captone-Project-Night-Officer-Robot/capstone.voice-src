"""
Telemetry API: receives pose + fall events from the Pi and broadcasts
them to map-dashboard clients over WebSocket.

State is in-memory per robot:
    path[robot_id]    = [{x, y, state, ts}, ...]
    falls[robot_id]   = [{x, y, ts}, ...]
    last_pose[robot_id] = {x, y, theta, state, ts}

The store is bounded (oldest path points drop after MAX_PATH_POINTS).
Multi-worker uvicorn would split this state across workers — keep
the API on `--workers 1` (the default) until persistence is added.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections import deque
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.core.logging import logger
from src.models.telemetry import (
    CallEvent,
    FallEvent,
    LogEvent,
    PatientEvent,
    PoseUpdate,
    TranscriptEvent,
)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


# ── store ─────────────────────────────────────────────────────────────────────

MAX_PATH_POINTS = 5000

# Only persist a new path point when the robot has moved at least this far
# (meters) from the last stored point. Keeps the dashboard polyline lean
# when the robot is parked during a voice session or fall.
MIN_MOVE_M = 0.03

_path: dict[str, list[dict]] = {}
_falls: dict[str, list[dict]] = {}
_last_pose: dict[str, dict] = {}
_last_metrics: dict[str, dict] = {}

# Live voice conversation transcript (per robot/room), latest patient record,
# and latest emergency-call status — all surfaced on the /app dashboard.
_MAX_TRANSCRIPT = 100
_transcript: dict[str, list[dict]] = {}
_patient: dict[str, dict] = {}
_call: dict[str, dict] = {}

# Ring buffer of recent log entries (API + worker + Pi). The dashboard
# replays this on connect so a freshly-opened tab isn't blank.
_LOG_BUFFER_MAX = 300
_log_buffer: deque[dict] = deque(maxlen=_LOG_BUFFER_MAX)

# Captured from main.lifespan so the loguru sink (which runs on whatever
# thread loguru picks) can post broadcasts back onto the API event loop.
_log_loop: asyncio.AbstractEventLoop | None = None

# WebSocket fan-out. FastAPI runs handlers on a single asyncio loop, so a
# plain set is fine without a lock.
_subscribers: set[WebSocket] = set()


def _snapshot() -> dict[str, Any]:
    robots: dict[str, Any] = {}
    keys = (
        set(_path) | set(_falls) | set(_last_pose) | set(_last_metrics)
        | set(_transcript) | set(_patient) | set(_call)
    )
    for robot_id in keys:
        robots[robot_id] = {
            "path": _path.get(robot_id, []),
            "falls": _falls.get(robot_id, []),
            "last_pose": _last_pose.get(robot_id),
            "metrics": _last_metrics.get(robot_id, {}),
            "transcript": _transcript.get(robot_id, []),
            "patient": _patient.get(robot_id),
            "call": _call.get(robot_id),
        }
    return {"robots": robots, "logs": list(_log_buffer)}


def set_log_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called once from main.lifespan to capture the API event loop."""
    global _log_loop
    _log_loop = loop


def _record_and_broadcast_log(entry: dict) -> None:
    """Append to ring buffer + push to all dashboard subscribers."""
    _log_buffer.append(entry)
    if _log_loop is None or _log_loop.is_closed():
        return
    try:
        asyncio.run_coroutine_threadsafe(
            _broadcast({"type": "log", **entry}), _log_loop
        )
    except Exception:
        pass


def loguru_broadcast_sink(message) -> None:  # type: ignore[no-untyped-def]
    """Loguru sink: fans every record out to dashboards via the WebSocket.

    Loguru may invoke this from a worker thread (we add the sink with
    enqueue=True), so we hop the broadcast back onto the API event loop.
    """
    rec = message.record
    entry = {
        "source": "api",
        "level": rec["level"].name,
        "message": rec["message"],
        "ts": rec["time"].timestamp(),
        "function": f"{rec['module']}.{rec['function']}",
    }
    _record_and_broadcast_log(entry)


async def _broadcast(message: dict) -> None:
    if not _subscribers:
        return
    dead: list[WebSocket] = []
    for ws in list(_subscribers):
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _subscribers.discard(ws)


# ── HTTP endpoints (called by the Pi) ─────────────────────────────────────────


@router.post("/pose", summary="Robot pose update")
async def post_pose(update: PoseUpdate) -> dict:
    point = {"x": update.x, "y": update.y, "state": update.state, "ts": update.ts}

    points = _path.setdefault(update.robot_id, [])
    if not points:
        points.append(point)
    else:
        last = points[-1]
        if math.hypot(update.x - last["x"], update.y - last["y"]) >= MIN_MOVE_M:
            points.append(point)
            if len(points) > MAX_PATH_POINTS:
                del points[: len(points) - MAX_PATH_POINTS]

    _last_pose[update.robot_id] = {
        "x": update.x,
        "y": update.y,
        "theta": update.theta,
        "state": update.state,
        "ts": update.ts,
    }

    if update.metrics:
        _last_metrics[update.robot_id] = dict(update.metrics)

    await _broadcast(
        {
            "type": "pose",
            "robot_id": update.robot_id,
            "x": update.x,
            "y": update.y,
            "theta": update.theta,
            "state": update.state,
            "ts": update.ts,
            "metrics": _last_metrics.get(update.robot_id, {}),
            "appended": points[-1] is point,
        }
    )
    return {"ok": True}


@router.post("/fall", summary="Fall event pin")
async def post_fall(event: FallEvent) -> dict:
    pin = {"x": event.x, "y": event.y, "ts": event.ts, "track_id": event.track_id}
    _falls.setdefault(event.robot_id, []).append(pin)
    logger.info(
        f"Fall pin recorded robot_id={event.robot_id} "
        f"x={event.x:.2f} y={event.y:.2f} track_id={event.track_id}"
    )
    await _broadcast({"type": "fall", "robot_id": event.robot_id, **pin})
    return {"ok": True}


@router.get("/snapshot", summary="Full path + falls for all robots")
async def get_snapshot() -> dict:
    return _snapshot()


@router.post("/log", summary="External log entry (worker / Pi / scripts)")
async def post_log(event: LogEvent) -> dict:
    entry = {
        "source": event.source,
        "level": event.level.upper(),
        "message": event.message,
        "ts": event.ts or time.time(),
        "function": event.function,
    }
    _log_buffer.append(entry)
    await _broadcast({"type": "log", **entry})
    return {"ok": True}


@router.post("/transcript", summary="Voice conversation line (STT/TTS)")
async def post_transcript(event: TranscriptEvent) -> dict:
    line = {
        "role": event.role,
        "text": event.text,
        "final": event.final,
        "ts": event.ts or time.time(),
    }
    # Interim (non-final) lines update in place on the client; we only persist
    # final lines in the replay buffer.
    if event.final:
        buf = _transcript.setdefault(event.robot_id, [])
        buf.append(line)
        if len(buf) > _MAX_TRANSCRIPT:
            del buf[: len(buf) - _MAX_TRANSCRIPT]
    await _broadcast({"type": "transcript", "robot_id": event.robot_id, **line})
    return {"ok": True}


@router.post("/patient", summary="Collected patient record")
async def post_patient(event: PatientEvent) -> dict:
    record = event.model_dump()
    record["ts"] = record.get("ts") or time.time()
    _patient[event.robot_id] = record
    await _broadcast({"type": "patient", **record})
    return {"ok": True}


@router.post("/call", summary="Emergency call status")
async def post_call(event: CallEvent) -> dict:
    status = event.model_dump()
    status["ts"] = status.get("ts") or time.time()
    _call[event.robot_id] = status
    logger.info(
        f"Emergency call status robot_id={event.robot_id} "
        f"status={event.status} to={event.to}"
    )
    await _broadcast({"type": "call", **status})
    return {"ok": True}


@router.post("/reset", summary="Clear stored telemetry")
async def reset(robot_id: str | None = None) -> dict:
    if robot_id is None:
        _path.clear()
        _falls.clear()
        _last_pose.clear()
        _last_metrics.clear()
        _transcript.clear()
        _patient.clear()
        _call.clear()
        _log_buffer.clear()
    else:
        _path.pop(robot_id, None)
        _falls.pop(robot_id, None)
        _last_pose.pop(robot_id, None)
        _last_metrics.pop(robot_id, None)
        _transcript.pop(robot_id, None)
        _patient.pop(robot_id, None)
        _call.pop(robot_id, None)
    await _broadcast({"type": "reset", "robot_id": robot_id})
    return {"ok": True}


# ── WebSocket (dashboard subscribes) ──────────────────────────────────────────


@router.websocket("/ws")
async def telemetry_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    _subscribers.add(websocket)
    try:
        await websocket.send_json({"type": "snapshot", **_snapshot()})
        # Keep the socket alive; we don't expect client → server messages.
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send a ping-equivalent so idle proxies don't kill the
                # connection.
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning(f"telemetry ws error: {exc}")
    finally:
        _subscribers.discard(websocket)
