from __future__ import annotations

from livekit.agents import Agent, RunContext, function_tool

from src.core.logging import logger
from src.prompts.prompts import GREETING_INSTRUCTION, SYSTEM_PROMPT
from src.services.notifier import PatientRecord, dispatch_emergency_alert


class NightOfficerAgent(Agent):
    """Voice agent with one Phase-2 tool: `dispatch_emergency`.

    The LLM calls the tool at Step 6 of the screening flow with everything it
    has gathered. The tool sends an SMS to the emergency contact via Twilio
    (see src/services/notifier.py) and returns a short confirmation string
    that the LLM uses to continue the conversation.
    """

    def __init__(self, robot_id: str | None = None) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self._robot_id = robot_id

    async def on_enter(self) -> None:
        logger.info("NightOfficerAgent entered room — sending greeting")
        await self.session.generate_reply(instructions=GREETING_INSTRUCTION)

    async def on_exit(self) -> None:
        logger.info("NightOfficerAgent exiting room")

    @function_tool
    async def dispatch_emergency(
        self,
        context: RunContext,
        patient_name: str = "",
        situation: str = "",
        pain_location: str = "",
        medical_conditions: str = "",
        medications: str = "",
        allergies: str = "",
        temperature: str = "",
        alcohol_consumed: str = "",
        notes: str = "",
    ) -> str:
        """Send the collected patient information to the on-call medical team
        via SMS and trigger the simulated emergency call. Call this once Step
        5 (alcohol check) is complete and BEFORE speaking the Step 6
        confirmation lines. Fill every field with the patient's own words;
        leave a field empty only if the patient declined or could not answer.

        Args:
            patient_name: Patient's stated name.
            situation: One short sentence describing what happened (Step 1).
            pain_location: Where the patient says it hurts (Step 3).
            medical_conditions: Existing conditions mentioned in Step 2.
            medications: Regular medications from Step 2.
            allergies: Known medical allergies from Step 3.
            temperature: Reading or self-report from Step 4 (or "unknown").
            alcohol_consumed: Patient's answer from Step 5.
            notes: Anything else the agent feels the medics should know.
        """
        record = PatientRecord(
            patient_name=patient_name,
            situation=situation,
            pain_location=pain_location,
            medical_conditions=medical_conditions,
            medications=medications,
            allergies=allergies,
            temperature=temperature,
            alcohol_consumed=alcohol_consumed,
            notes=notes,
        )
        result = await dispatch_emergency_alert(record, robot_id=self._robot_id)
        if result.get("ok"):
            return (
                "Emergency SMS sent successfully. Confirm to the patient that "
                "help is on the way and continue with Step 6."
            )
        return (
            "Emergency dispatch could not be sent over the network "
            f"({result.get('reason', 'unknown')}). Reassure the patient and "
            "continue with the Step 6 confirmation lines anyway."
        )