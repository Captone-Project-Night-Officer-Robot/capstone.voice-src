from __future__ import annotations

import asyncio

from dataclasses import asdict

from livekit.agents import Agent, RunContext, function_tool

from src.client.dashboard import push_patient
from src.core.logging import logger
from src.prompts.prompts import GREETING_INSTRUCTION, SYSTEM_PROMPT
from src.services.emergency_call import place_emergency_call
from src.services.notifier import PatientRecord, dispatch_emergency_alert


class NightOfficerAgent(Agent):
    """Voice agent with one tool: `dispatch_emergency`.

    The LLM calls the tool at Step 3 (DISPATCH) — the moment it says "I am
    calling one one nine now". The tool sends the SMS AND places the outbound
    emergency phone call (a second agent reports the record over the phone),
    then returns a short confirmation string the LLM uses to continue.
    """

    def __init__(self, robot_id: str | None = None) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self._robot_id = robot_id
        self._emergency_called = False
        # Keep a strong reference to the background call task so it isn't
        # garbage-collected before it finishes.
        self._call_task: asyncio.Task | None = None

    async def on_enter(self) -> None:
        logger.info("NightOfficerAgent entered room — sending greeting")
        await self.session.generate_reply(instructions=GREETING_INSTRUCTION)

    async def on_exit(self) -> None:
        logger.info("NightOfficerAgent exiting room")

    async def _do_emergency_call(self, record: PatientRecord) -> None:
        """Place the outbound emergency call in the background."""
        result = await place_emergency_call(record, robot_id=self._robot_id)
        if not result.get("ok"):
            logger.warning(
                f"Emergency call not placed: {result.get('reason', 'unknown')}"
            )

    @function_tool
    async def dispatch_emergency(
        self,
        context: RunContext,
        patient_name: str = "",
        situation: str = "",
        pain_location: str = "",
        temperature: str = "",
        medical_conditions: str = "",
        medications: str = "",
        allergies: str = "",
        alcohol_consumed: str = "",
        notes: str = "",
    ) -> str:
        """Dispatch help: text the medical team AND place the emergency phone call.

        Call this at STEP 3 (DISPATCH), exactly when you say "I am calling one
        one nine now". Call it once. Fill every field you have with the
        patient's own words; leave a field empty only if they did not answer.
        Do not wait for the rest of the conversation — call it now so the phone
        call goes out immediately while you keep comforting the patient.

        Args:
            patient_name: Patient's stated name (Step 1).
            situation: One short sentence on what happened (Step 1).
            pain_location: Where the patient says it hurts (Step 1).
            temperature: Reading or self-report from Step 2 (or "unknown").
            medical_conditions: Any conditions the patient mentioned.
            medications: Any regular medications mentioned.
            allergies: Any known medical allergies mentioned.
            alcohol_consumed: Whether they mentioned drinking (or "unknown").
            notes: Anything else the medics should know.
        """
        record = PatientRecord(
            patient_name=patient_name,
            situation=situation,
            pain_location=pain_location,
            temperature=temperature,
            medical_conditions=medical_conditions,
            medications=medications,
            allergies=allergies,
            alcohol_consumed=alcohol_consumed,
            notes=notes,
        )

        # Surface the collected record on the dashboard immediately.
        if self._robot_id:
            await push_patient(self._robot_id, asdict(record))

        # Send the SMS (awaited — fast) and kick off the phone call in the
        # background so this tool returns immediately and the agent can keep
        # talking to the patient while the phone rings.
        sms = await dispatch_emergency_alert(record, robot_id=self._robot_id)

        if not self._emergency_called:
            self._emergency_called = True
            logger.info("Step 3 dispatch — placing emergency call now")
            self._call_task = asyncio.create_task(self._do_emergency_call(record))

        if sms.get("ok"):
            return (
                "Dispatch sent and the emergency call is being placed. Confirm "
                "to the patient that help is on the way and continue."
            )
        return (
            "The text could not be sent, but the emergency call is being placed. "
            "Reassure the patient that help is on the way and continue."
        )
