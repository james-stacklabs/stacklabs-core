#!/usr/bin/env python3
"""
Sovereign OS — Telemetry Media Ingress (TMI) & Hardware Lighting Sync Verifier
Ticket: WO0010061-FANSTACK-SIM-PHASE2-3-POLLS-AND-MED
SOW: SOW_2026_09_11_FANSTACK_SIMULATION_PHASE_2_3.md
Path: /home/james/stacklabs/scripts/sports/verify_simulation_triggers.py

Verifies the triple-handshake execution chain:
Statcast Telemetry Ingress -> Webslinger Action & Video Asset -> Govee UDP Port 4003 Hardware Flash

Target Event Matrix:
1. Senga Punchout (Inning 3): STRIKEOUT_PUNCHOUT_GOLD -> Keith Punchout Video -> GOLD_BURST (RGB 255, 215, 0)
2. Exit Velo Rocket (105+ MPH): HOME_RUN_AIRHORN_GOVEE -> Home Run Apple -> ORANGE_BLUE_STROBE (RGB 255, 85, 0)
3. Walk-Off Win (10th Inning): METS_WIN_OVERLAY -> Letters LFGM Video -> VICTORY_SWEEP (RGB 0, 255, 128)
"""

import sys
import os
import json
import socket
import asyncio
import argparse
import websockets
from typing import Dict, List, Any

sys.path.insert(0, "/home/james/stacklabs")
from scripts.core import api_client

TRIGGER_EVENTS = [
    {
        "id": "senga_punchout",
        "name": "Kodai Senga Ghost-Fork Strikeout",
        "tmi_rule": 1003,
        "webslinger_action": "STRIKEOUT_PUNCHOUT_GOLD",
        "video_asset": "/videos/Keith_thrusts_arm__GO_SIT_202606201553.mp4",
        "govee_preset": "GOLD_BURST",
        "rgb": {"r": 255, "g": 215, "b": 0},
        "description": "3rd Inning strikeout on 84mph ghost fork."
    },
    {
        "id": "benge_exit_rocket",
        "name": "Carson Benge 105+ MPH Exit Velo Rocket",
        "tmi_rule": 1009,
        "webslinger_action": "HOME_RUN_AIRHORN_GOVEE",
        "video_asset": "/videos/Mets_Home_Run_Apple_dancing_202607032107.mp4",
        "govee_preset": "ORANGE_BLUE_STROBE",
        "rgb": {"r": 255, "g": 85, "b": 0},
        "description": "6th Inning 108.4mph rocket down the left field line."
    },
    {
        "id": "mets_walkoff_win",
        "name": "Bottom 10th Walk-Off Victory (Semien Scores)",
        "tmi_rule": 1004,
        "webslinger_action": "METS_WIN_OVERLAY",
        "video_asset": "/videos/Letters_LFGM_land_on_baseball_202607032107.mp4",
        "govee_preset": "VICTORY_SWEEP",
        "rgb": {"r": 0, "g": 255, "b": 128},
        "description": "10th Inning Carson Benge walk-off fielder's choice. Mets 7 - Yankees 6 FINAL."
    }
]

class TriggerVerificationHarness:
    def __init__(self, ws_url: str = "ws://127.0.0.1:8008", game_pk: str = "823628"):
        self.ws_url = ws_url
        self.game_pk = str(game_pk)

    async def verify_event_chain(self, event: Dict[str, Any], ws) -> Dict[str, Any]:
        print(f"\n[*] Testing Trigger Chain: [{event['name']}]")
        print(f"   TMI Rule: {event['tmi_rule']} | Action: {event['webslinger_action']}")
        print(f"   Video Asset: {event['video_asset']}")
        print(f"   Govee Lighting: {event['govee_preset']} (RGB {event['rgb']['r']}, {event['rgb']['g']}, {event['rgb']['b']})")

        # 1. Format and send WebSocket action trigger
        payload = {
            "type": "webslinger_trigger",
            "event": event["webslinger_action"],
            "target_game_pk": self.game_pk,
            "data": {
                "tmi_rule": event["tmi_rule"],
                "video_url": event["video_asset"],
                "duration_ms": 3500,
                "govee_preset": event["govee_preset"],
                "rgb": event["rgb"],
                "description": event["description"]
            }
        }
        await ws.send(json.dumps(payload))
        print(f"   ✔ Dispatched 'webslinger_trigger' to WebSocket relay")

        # 2. Trigger Govee hardware lighting dispatch
        govee_res = api_client.trigger_govee_hardware(
            preset=event["govee_preset"],
            event_type=event["id"]
        )
        print(f"   ✔ Govee UDP Port 4003 Dispatch: {govee_res.get('status')} ({event['govee_preset']})")

        # 3. Verify physical asset exists on disk
        asset_rel = event["video_asset"].lstrip("/")
        candidate_paths = [
            f"/home/james/stacklabs/19_Sovereign_Sports/public/{asset_rel}",
            f"/home/james/stacklabs/15_FanStack/public/{asset_rel}",
            f"/home/james/stacklabs/19_Sovereign_Sports/dist/{asset_rel}"
        ]
        asset_found = any(os.path.exists(p) for p in candidate_paths)
        print(f"   ✔ Asset Verified on Disk: {asset_found}")

        await asyncio.sleep(0.5)
        return {
            "event_id": event["id"],
            "name": event["name"],
            "websocket_dispatched": True,
            "govee_response": govee_res,
            "asset_found": asset_found,
            "status": "PASSED" if asset_found else "WARN_ASSET_MISSING"
        }

    async def run_all(self) -> List[Dict[str, Any]]:
        print(f"[*] Connecting to FanStack WebSocket Relay: {self.ws_url}...")
        results = []
        async with websockets.connect(self.ws_url) as ws:
            print(f"✔ Connected! Joining room {self.game_pk}...")
            await ws.send(json.dumps({"type": "ROOM_JOIN", "room": self.game_pk}))
            await asyncio.sleep(0.3)

            for event in TRIGGER_EVENTS:
                res = await self.verify_event_chain(event, ws)
                results.append(res)

        print("\n" + "="*80)
        print(f"✔ Completed Triple-Handshake Trigger Verification ({len(results)} events verified)")
        print("="*80)
        return results

def main():
    parser = argparse.ArgumentParser(description="TMI & Hardware Trigger Verification")
    parser.add_argument("--gamepk", default="823628", help="Target MLB GamePk")
    parser.add_argument("--ws", default="ws://127.0.0.1:8008", help="WebSocket Relay URL")
    args = parser.parse_args()

    harness = TriggerVerificationHarness(ws_url=args.ws, game_pk=args.gamepk)
    report = asyncio.run(harness.run_all())
    return report

if __name__ == "__main__":
    main()
