"""
Place a bare outbound SIP call to verify the trunk works — NO agent, NO audio.

Dials --to into a fresh LiveKit room using LIVEKIT_SIP_OUTBOUND_TRUNK_ID.
Your phone should ring and connect. There is no audio yet (nothing is in the
room to talk); this step only proves LiveKit → Twilio → PSTN is wired up.

Once this rings, the SIP path is good and we can drop the EmergencyDispatch
agent into the room next.

Usage (run from capstone.voice-src/ so .env is found):

  python scripts/test_outbound_call.py --to +12313102506

⚠️ On a Twilio trial account you can only call VERIFIED numbers.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import uuid

from dotenv import load_dotenv
from livekit import api


async def main() -> None:
    load_dotenv()

    p = argparse.ArgumentParser()
    p.add_argument("--to", required=True, help="Destination phone number, E.164 (+1...)")
    p.add_argument(
        "--trunk",
        default=os.environ.get("LIVEKIT_SIP_OUTBOUND_TRUNK_ID"),
        help="Outbound trunk id (default: LIVEKIT_SIP_OUTBOUND_TRUNK_ID from .env)",
    )
    p.add_argument("--room", default=f"sip-test-{uuid.uuid4().hex[:8]}")
    args = p.parse_args()

    if not args.trunk:
        raise SystemExit(
            "No trunk id. Set LIVEKIT_SIP_OUTBOUND_TRUNK_ID in .env "
            "(run create_sip_trunk.py first) or pass --trunk ST_..."
        )

    lkapi = api.LiveKitAPI()
    try:
        print(f"Dialing {args.to} into room '{args.room}' via {args.trunk} ...")
        resp = await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=args.trunk,
                sip_call_to=args.to,
                room_name=args.room,
                participant_identity="sip-callee",
                participant_name="Test Callee",
            )
        )
        print(f"✅ SIP participant created: {resp.participant_identity}")
        print("Your phone should be ringing. (No audio — no agent yet.)")
        print("Answer to confirm the trunk works, then hang up.")
    except Exception as exc:
        print(f"❌ Call failed: {type(exc).__name__}: {exc}")
        print(
            "Common causes: Termination auth not set (credential list), "
            "geo-permissions disabled for the destination, or trial account "
            "calling an unverified number."
        )
    finally:
        await lkapi.aclose()


if __name__ == "__main__":
    asyncio.run(main())
