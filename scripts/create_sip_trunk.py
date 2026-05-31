"""
Create the LiveKit SIP *outbound* trunk that points at your Twilio Elastic
SIP Trunk, so LiveKit can place outbound PSTN (phone) calls.

Run this ONCE. It prints a trunk id (ST_...) — put that in .env as
LIVEKIT_SIP_OUTBOUND_TRUNK_ID.

Twilio prerequisites (Elastic SIP Trunking → your "night-officer" trunk):
  • Termination SIP URI created   (e.g. totwAb-xihhuj-1qyvxo.pstn.twilio.com)
  • Termination Authentication: a Credential List (username + password)
  • A phone number assigned to the trunk (used as caller ID)
  • Voice dialing / geo-permissions enabled for the destination country

Usage (run from the capstone.voice-src/ directory so .env is found):

  python scripts/create_sip_trunk.py \
    --address totwAb-xihhuj-1qyvxo.pstn.twilio.com \
    --number +12313102506 \
    --username <your-credential-list-username> \
    --password <your-credential-list-password>
"""

from __future__ import annotations

import argparse
import asyncio

from dotenv import load_dotenv
from livekit import api


async def main() -> None:
    load_dotenv()  # reads LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET

    p = argparse.ArgumentParser()
    p.add_argument(
        "--address", required=True,
        help="Twilio Termination SIP URI host, e.g. xxxx.pstn.twilio.com",
    )
    p.add_argument(
        "--number", required=True, action="append",
        help="Twilio caller-ID number in E.164 (repeat --number for more).",
    )
    p.add_argument("--username", required=True, help="Twilio credential-list username")
    p.add_argument("--password", required=True, help="Twilio credential-list password")
    p.add_argument("--name", default="night-officer-outbound")
    args = p.parse_args()

    lkapi = api.LiveKitAPI()
    try:
        trunk = api.SIPOutboundTrunkInfo(
            name=args.name,
            address=args.address,
            numbers=args.number,
            auth_username=args.username,
            auth_password=args.password,
        )
        resp = await lkapi.sip.create_outbound_trunk(
            api.CreateSIPOutboundTrunkRequest(trunk=trunk)
        )
        print("\n✅ Created LiveKit outbound trunk:")
        print(f"   sip_trunk_id : {resp.sip_trunk_id}")
        print(f"   address      : {resp.address}")
        print(f"   numbers      : {list(resp.numbers)}")
        print("\nAdd this line to capstone.voice-src/.env:")
        print(f"\n   LIVEKIT_SIP_OUTBOUND_TRUNK_ID={resp.sip_trunk_id}\n")
    finally:
        await lkapi.aclose()


if __name__ == "__main__":
    asyncio.run(main())
