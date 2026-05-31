from __future__ import annotations

from livekit.agents import Agent

from src.core.logging import logger
from src.prompts.prompts import (
    EMERGENCY_GREETING_INSTRUCTION,
    build_emergency_prompt,
)
from src.services.notifier import PatientRecord


class EmergencyDispatchAgent(Agent):
    """Second agent that runs on the outbound phone call.

    Seeded with the PatientRecord collected by the NightOfficerAgent, it
    reports the patient's situation to the emergency contact in English then
    Korean, answers questions from the record, and ends the call.
    """

    def __init__(self, record: PatientRecord, robot_id: str | None = None) -> None:
        super().__init__(instructions=build_emergency_prompt(record, robot_id))
        self._record = record
        self._robot_id = robot_id

    async def on_enter(self) -> None:
        logger.info(
            "EmergencyDispatchAgent on call — delivering patient report",
            extra={"robot_id": self._robot_id},
        )
        await self.session.generate_reply(instructions=EMERGENCY_GREETING_INSTRUCTION)

    async def on_exit(self) -> None:
        logger.info("EmergencyDispatchAgent ending call")
