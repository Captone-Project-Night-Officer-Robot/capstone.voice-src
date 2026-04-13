from __future__ import annotations

from livekit.agents import WorkerOptions, cli

from src.agent.session import start_agent_session
from src.core.config import settings
from src.core.logging import logger


if __name__ == "__main__":
    logger.info(f"Starting Night Officer agent worker — log level: {settings.log_level}")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=start_agent_session,
        )
    )