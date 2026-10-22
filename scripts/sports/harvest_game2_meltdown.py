#!/usr/bin/env python3
"""
Sovereign OS: Game 2 Meltdown Harvester (WO0010154)
Ground Truth: /home/james/stacklabs/dna/cache/mlb_823574_feed.json
Target: BAL @ NYM (Sept 15, 2026, Game PK 823574, Citi Field)
Key Moments:
  - Play 63 (Top 9th): Pete Alonso 2-run HR (36) off Kodai Senga (107.4 mph, 412 ft)
  - Play 83 (Top 11th): Coby Mayo 3-run inside-the-park HR (24) off Jonathan Pintaro
Advocates: Queens 4 (@barf, @7_train_terry, @UncleStevieStan, @keith_fanboy)
           Baltimore 2 (@birdland_boomer, @dirty_water_danny)
Output: /home/james/sovereign_inbox/pilot_drops/harvested_meltdown_reactions_823574.json
"""

import os
import sys
import json
import time
import asyncio
import urllib.request
import websockets

PORTAL_API = "http://127.0.0.1:8095"
WS_URL = "ws://127.0.0.1:8008"
GAME_PK = "823574"
OUTPUT_FILE = "/home/james/sovereign_inbox/pilot_drops/harvested_meltdown_reactions_823574.json"

TARGET_ADVOCATES = {
    "queens_4": ["barf", "7_train_terry", "UncleStevieStan", "keith_fanboy"],
    "baltimore_2": ["birdland_boomer", "dirty_water_danny"]
}
ALL_ADVOCATES = TARGET_ADVOCATES["queens_4"] + TARGET_ADVOCATES["baltimore_2"]

def clean_environment():
    """Ensure bot mute flag is gone."""
    flag_path = "/tmp/bots_paused.flag"
    if os.path.exists(flag_path):
        os.remove(flag_path)
        print(f"[CLEAN] Unlinked {flag_path}")

def call_api(endpoint: str, data: dict = None, method: str = "POST"):
    url = f"{PORTAL_API}{endpoint}"
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method=method
    )
    with urllib.request.urlopen(req, timeout=15.0) as resp:
        return json.loads(resp.read().decode("utf-8"))

async def harvest_meltdowns():
    clean_environment()
    print("[1] Loading 2026 Statcast Simulation for Game PK 823574...")
    load_res = call_api("/api/sports/sim/load", {"game_pk": GAME_PK})
    print(f"    ✔ Loaded sim: {load_res.get('teams')} at {load_res.get('venue')}, {load_res.get('total_plays')} plays")

    harvested_data = {
        "metadata": {
            "ticket_id": "WO0010154",
            "game_pk": GAME_PK,
            "matchup": "BAL @ NYM",
            "date": "2026-09-15",
            "venue": "Citi Field",
            "statcast_feed": "/home/james/stacklabs/dna/cache/mlb_823574_feed.json",
            "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "engine": "Vertex AI (gemini-3.8-flash)",
            "boggs_level": 5
        },
        "key_plays": {
            "play_63_alonso_tying_hr": {
                "inning": "Top 9",
                "outs": 1,
                "count": "1-2",
                "batter": "Pete Alonso (BAL #20)",
                "pitcher": "Kodai Senga (NYM)",
                "exit_velocity_mph": 107.4,
                "launch_angle_deg": 35.0,
                "distance_ft": 412,
                "description": "Pete Alonso homers (36) on a fly ball to left center field off Kodai Senga to tie the game 3-3 in the 9th inning.",
                "reactions": []
            },
            "play_83_mayo_inside_park_hr": {
                "inning": "Top 11",
                "outs": 1,
                "batter": "Coby Mayo (BAL #24)",
                "pitcher": "Jonathan Pintaro (NYM)",
                "exit_velocity_mph": 106.9,
                "launch_angle_deg": 25.0,
                "distance_ft": 410,
                "description": "Coby Mayo hits an inside-the-park home run (24) on a fly ball to center field off Jonathan Pintaro, scoring Leody Taveras and Dylan Beavers to blow open the game.",
                "reactions": []
            }
        },
        "advocate_roster": {
            "queens_4_mets": TARGET_ADVOCATES["queens_4"],
            "baltimore_2_orioles": TARGET_ADVOCATES["baltimore_2"]
        }
    }

    async with websockets.connect(WS_URL) as ws:
        print("[2] Connected to WebSocket mesh on Port 8008.")
        await ws.send(json.dumps({"type": "JOIN_ROOM", "room": GAME_PK, "target_game_pk": GAME_PK}))
        await ws.send(json.dumps({"type": "boggs_level", "level": 5}))

        # Queue for incoming messages
        incoming_msgs = asyncio.Queue()

        async def ws_reader():
            try:
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        mtype = data.get("type")
                        if mtype in ("CHAT_MESSAGE", "ROOM_CHAT", "CHAT"):
                            user = data.get("user") or data.get("persona") or ""
                            room = str(data.get("target_game_pk") or data.get("room") or "")
                            text = data.get("text") or ""
                            if room in (GAME_PK, "GLOBAL", ""):
                                await incoming_msgs.put({"user": user, "text": text, "time": time.strftime("%H:%M:%S")})
                    except Exception:
                        pass
            except asyncio.CancelledError:
                pass

        reader_task = asyncio.create_task(ws_reader())

        # ----------------------------------------------------
        # MOMENT 1: Play 63 - Pete Alonso 9th Inning HR off Senga
        # ----------------------------------------------------
        print("\n[3] Triggering MOMENT 1: Play 63 (Pete Alonso tying HR off Senga)...")
        call_api("/api/sports/sim/control", {"action": "jump", "index": 63})

        alonso_reactions = {}
        t0 = time.time()
        
        # Trigger explicit prompts for all 6 advocates if they haven't spoken
        for persona in ALL_ADVOCATES:
            team = "NYM" if persona in TARGET_ADVOCATES["queens_4"] else "BAL"
            if team == "NYM":
                instr = (
                    f"MOMENT: TOP 9TH, 1 OUT. Pete Alonso just hit a game-tying 2-run HOME RUN off Kodai Senga "
                    f"into left-center (107.4 mph, 412 ft)! Alonso is wearing Baltimore orange and black #20. "
                    f"The game is tied 3-3. Citi Field is stunned and mourning. Senga blew the save. "
                    f"React with pure agony, disbelief, and heartbreak in character! Maximum 35 words."
                )
            else:
                instr = (
                    f"MOMENT: TOP 9TH, 1 OUT. Pete Alonso just hit a game-tying 2-run HOME RUN off Kodai Senga "
                    f"into left-center (107.4 mph, 412 ft)! The Polar Bear ties it 3-3 at Citi Field wearing orange and black! "
                    f"React with pure Baltimore ecstasy and bragging rights! Maximum 35 words."
                )
            await ws.send(json.dumps({
                "type": "custom_prompt",
                "persona": persona,
                "prompt": instr,
                "target_game_pk": GAME_PK
            }))
            await asyncio.sleep(0.4)

        # Collect for 15 seconds or until all 6 responded
        while time.time() - t0 < 18.0 and len(alonso_reactions) < len(ALL_ADVOCATES):
            try:
                msg = await asyncio.wait_for(incoming_msgs.get(), timeout=2.0)
                u = msg["user"].lstrip("@")
                for target in ALL_ADVOCATES:
                    if target.lower() == u.lower() and target not in alonso_reactions:
                        alonso_reactions[target] = msg
                        print(f"    [Play 63] @{target}: {msg['text']}")
            except asyncio.TimeoutError:
                pass

        print(f"✔ Collected {len(alonso_reactions)} reactions for Play 63.")
        harvested_data["key_plays"]["play_63_alonso_tying_hr"]["reactions"] = [
            {"persona": f"@{k}", "team": "NYM" if k in TARGET_ADVOCATES["queens_4"] else "BAL", "text": v["text"], "timestamp": v["time"]}
            for k, v in alonso_reactions.items()
        ]

        # ----------------------------------------------------
        # MOMENT 2: Play 83 - Coby Mayo 11th Inning Inside-the-Park HR off Pintaro
        # ----------------------------------------------------
        print("\n[4] Triggering MOMENT 2: Play 83 (Coby Mayo inside-the-park HR off Pintaro)...")
        call_api("/api/sports/sim/control", {"action": "jump", "index": 83})

        mayo_reactions = {}
        t1 = time.time()

        for persona in ALL_ADVOCATES:
            team = "NYM" if persona in TARGET_ADVOCATES["queens_4"] else "BAL"
            if team == "NYM":
                instr = (
                    f"MOMENT: TOP 11TH INNING. Jonathan Pintaro gave up a 3-run inside-the-park HOME RUN to Coby Mayo! "
                    f"Mayo hit it 410 ft to center and circled the bases while the Mets defense collapsed. "
                    f"Total Mets bullpen meltdown and implosion. React with complete catastrophic despair! Maximum 35 words."
                )
            else:
                instr = (
                    f"MOMENT: TOP 11TH INNING. Coby Mayo just hit a 3-RUN INSIDE-THE-PARK HOME RUN off Jonathan Pintaro! "
                    f"The big man is chugging around the bases and slides into home! Baltimore takes the lead in extras! "
                    f"React with insane hype and celebration! Maximum 35 words."
                )
            await ws.send(json.dumps({
                "type": "custom_prompt",
                "persona": persona,
                "prompt": instr,
                "target_game_pk": GAME_PK
            }))
            await asyncio.sleep(0.4)

        while time.time() - t1 < 18.0 and len(mayo_reactions) < len(ALL_ADVOCATES):
            try:
                msg = await asyncio.wait_for(incoming_msgs.get(), timeout=2.0)
                u = msg["user"].lstrip("@")
                for target in ALL_ADVOCATES:
                    if target.lower() == u.lower() and target not in mayo_reactions:
                        mayo_reactions[target] = msg
                        print(f"    [Play 83] @{target}: {msg['text']}")
            except asyncio.TimeoutError:
                pass

        print(f"✔ Collected {len(mayo_reactions)} reactions for Play 83.")
        harvested_data["key_plays"]["play_83_mayo_inside_park_hr"]["reactions"] = [
            {"persona": f"@{k}", "team": "NYM" if k in TARGET_ADVOCATES["queens_4"] else "BAL", "text": v["text"], "timestamp": v["time"]}
            for k, v in mayo_reactions.items()
        ]

        reader_task.cancel()

    # Write output to disk
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(harvested_data, f, indent=2)
    print(f"\n[5] Meltdown harvest recorded to {OUTPUT_FILE}")
    print(f"    Total Alonso reactions: {len(harvested_data['key_plays']['play_63_alonso_tying_hr']['reactions'])}")
    print(f"    Total Mayo reactions: {len(harvested_data['key_plays']['play_83_mayo_inside_park_hr']['reactions'])}")

if __name__ == "__main__":
    asyncio.run(harvest_meltdowns())
