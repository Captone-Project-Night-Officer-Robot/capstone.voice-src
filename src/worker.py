from __future__ import annotations

import os

import httpx
from livekit.agents import WorkerOptions, cli

from src.agent.session import start_agent_session
from src.core.config import settings
from src.core.logging import logger


# Where to push agent-side logs so the dashboard can show them. Defaults to
# the local API; override via DASHBOARD_LOG_URL if the worker and API run
# on different hosts.
_LOG_INGEST_URL = os.environ.get(
    "DASHBOARD_LOG_URL",
    f"http://{settings.host if settings.host != '0.0.0.0' else 'localhost'}"
    f":{settings.port}/api/v1/telemetry/log",
)

_http = httpx.Client(timeout=1.0)


def _dashboard_log_sink(message) -> None:  # type: ignore[no-untyped-def]
    """Loguru sink that ships agent-worker logs to the API for fan-out.

    Best-effort. A failed POST never blocks the agent — loguru calls this
    on a background thread (enqueue=True) and we swallow exceptions.
    """
    rec = message.record
    try:
        _http.post(
            _LOG_INGEST_URL,
            json={
                "source": "worker",
                "level": rec["level"].name,
                "message": rec["message"],
                "ts": rec["time"].timestamp(),
                "function": f"{rec['module']}.{rec['function']}",
            },
        )
    except Exception:
        pass


if __name__ == "__main__":
    logger.add(_dashboard_log_sink, level=settings.log_level, enqueue=True)
    logger.info(f"Starting Night Officer agent worker — log level: {settings.log_level}")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=start_agent_session,
            # Cold-importing the ML stack (torch + onnxruntime via Silero VAD
            # and the MultilingualModel turn detector) takes 20-60s on slower
            # machines. The 10s default kills the job process mid-init with a
            # TimeoutError, so the agent never joins the room. 60s is safe.
            initialize_process_timeout=60.0,
        )
    )