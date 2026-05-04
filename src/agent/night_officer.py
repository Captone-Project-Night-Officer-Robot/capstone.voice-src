from __future__ import annotations

from livekit.agents import Agent

from src.core.logging import logger
from src.prompts.prompts import GREETING_INSTRUCTION, SYSTEM_PROMPT


class NightOfficerAgent(Agent):
    """
    Phase 1 — speak only.
    Phase 2 — add @function_tool for dispatch_alert / log_triage_result.
    """

    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    async def on_enter(self) -> None:
        logger.info("NightOfficerAgent entered room — sending greeting")
        await self.session.generate_reply(instructions=GREETING_INSTRUCTION)

    async def on_exit(self) -> None:
        logger.info("NightOfficerAgent exiting room")