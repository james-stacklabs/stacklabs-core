#!/usr/bin/env python3
import asyncio
import websockets
import json
import sqlite3
import random
import uuid
import datetime
import argparse
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
WS_URL = "ws://localhost:8008"

# 4 pre-seeded hooligan personas
PERSONAS = [
    {"user": "proper_pinter", "color": "#FB923C", "quotes": [
        "That tackle should have drawn blood! Ref has lost the plot entirely!",
        "VAR is killing the soul of the terrace! In my day we kept playing!",
        "Foul? Back in my day that was a friendly greeting. Soft!",
        "Get the ball forward, none of this sideways nonsense!"
    ]},
    {"user": "expected_tears", "color": "#38BDF8", "quotes": [
        "A low-xG goal from there is statistical noise. Absolutely ridiculous.",
        "The transition matrix predicted this exact concession. Our midfield shape is fatal.",
        "Underlying statistics do not lie. We are mathematically doomed.",
        "xG delta is now 1.25. Statistically speaking, we are losing our tactical integrity."
    ]},
    {"user": "ultra_nip", "color": "#F43F5E", "quotes": [
        "LIGHT UP THE FLARES! NO PYRO NO PARTY! 🔥🔥🔥",
        "Absolute referee conspiracy! They don't want us to win!",
        "SCREAM UNTIL YOUR LUNGS GIVE OUT! USA! USA!",
        "We stand strong! Nobody takes our terrace!"
    ]},
    {"user": "kit_collector_99", "color": "#10B981", "quotes": [
        "Did you see that vintage 94 knit collar? Absolute masterpiece.",
        "The typography on the numbers is a design crime. Needs sans-serif.",
        "Love the jersey, but the sponsor logo placement is ruining the layout flow.",
        "That pitch pattern matches our new limited edition windbreaker drops."
    ]}
]

def insert_incident(match_id, match_minute, incident_type, leverage_delta, payload):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        incident_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO soccer_incident_ingress (incident_id, match_id, match_minute, incident_type, leverage_delta, data_payload) VALUES (?, ?, ?, ?, ?, ?)",
            (incident_id, match_id, str(match_minute), incident_type, leverage_delta, json.dumps(payload))
        )
        conn.commit()
        conn.close()
        return incident_id
    except Exception as e:
        print(f"[Footy Poller] DB insert error: {e}", file=sys.stderr)
        return None

async def broadcast_event(ws, event_data):
    if ws:
        try:
            await ws.send(json.dumps(event_data))
        except Exception as e:
            print(f"[Footy Poller] WebSocket broadcast error: {e}", file=sys.stderr)

async def run_simulation(match_id, ws_client):
    print(f"[Footy Poller] Starting mock match simulation for Match {match_id}")
    
    minutes = [75, 76, 78, 80, 82, 85, 88, 90]
    incidents = [
        {"type": "FOUL", "leverage_delta": -0.1, "desc": "Crunching slide tackle in midfield"},
        {"type": "YELLOW_CARD", "leverage_delta": -0.2, "desc": "Yellow card for tactical foul"},
        {"type": "SHOT_ON_TARGET", "leverage_delta": 0.4, "desc": "Power shot tipped over the crossbar"},
        {"type": "VAR_REVIEW", "leverage_delta": 0.0, "desc": "VAR penalty check for hand ball"},
        {"type": "GOAL", "leverage_delta": 1.5, "desc": "STUNNING GOAL INTO THE TOP CORNER!"},
        {"type": "SMOKE_FLARE", "leverage_delta": 0.1, "desc": "Hooligan smoke flare ignited in Section 104"},
        {"type": "SUBSTITUTION", "leverage_delta": 0.1, "desc": "Tactical change: attacking midfielder on"}
    ]

    for minute in minutes:
        await asyncio.sleep(8)  # Simulation speed: 8 seconds per match event
        
        inc = random.choice(incidents)
        payload = {"description": inc["desc"], "match_id": match_id, "minute": minute}
        
        # Write to Database
        insert_incident(match_id, minute, inc["type"], inc["leverage_delta"], payload)
        print(f"[Footy Poller] Event recorded: {minute}' {inc['type']} - {inc['desc']}")
        
        # Broadcast Event to websocket listeners
        ws_event = {
            "type": "CHAT_MESSAGE",
            "user": "OptaLiveFeed",
            "text": f"🚨 {minute}' {inc['type']}: {inc['desc']}",
            "color": "#E11D48",
            "time": f"{minute}:00"
        }
        await broadcast_event(ws_client, ws_event)
        
        # Hooligans react!
        await asyncio.sleep(2)
        
        # Pick 2 random personas to react
        reactors = random.sample(PERSONAS, 2)
        for bot in reactors:
            # Special case for ultra_nip and smoke flares
            quote = random.choice(bot["quotes"])
            if inc["type"] == "GOAL" and bot["user"] == "ultra_nip":
                quote = "GOAAAAALLL!! LIGHT IT UP! 🔥🔥🔥 RED SMOKE OVER THE PITCH!"
            elif inc["type"] == "VAR_REVIEW" and bot["user"] == "proper_pinter":
                quote = "Unbelievable! VAR is ruining the beautiful game! Let them play!"
                
            bot_event = {
                "type": "CHAT_MESSAGE",
                "user": bot["user"],
                "text": quote,
                "color": bot["color"],
                "time": f"{minute}:15"
            }
            await broadcast_event(ws_client, bot_event)
            await asyncio.sleep(1)

async def main():
    parser = argparse.ArgumentParser(description="Footy Ingress Telemetry Poller & Simulator")
    parser.add_argument("--mock-match-id", type=int, default=991002, help="Match ID to simulate")
    parser.add_argument("--emit-test-goal", action="store_true", help="Emit a single test goal event immediately and exit")
    args = parser.parse_args()

    # Establish websocket connection
    ws_client = None
    try:
        ws_client = await websockets.connect(WS_URL)
        print(f"[Footy Poller] Connected to WebSocket at {WS_URL}")
    except Exception as e:
        print(f"[Footy Poller] Could not connect to WebSocket: {e}. Running offline-only database updates.", file=sys.stderr)

    if args.emit_test_goal:
        # Immediate test goal event
        payload = {"description": "Immediate Test Goal Scored!", "match_id": args.mock_match_id, "minute": 90}
        insert_incident(args.mock_match_id, 90, "GOAL", 1.5, payload)
        
        ws_event = {
            "type": "CHAT_MESSAGE",
            "user": "OptaLiveFeed",
            "text": "🚨 90' GOAL: Immediate Test Goal Scored!",
            "color": "#E11D48",
            "time": "90:00"
        }
        await broadcast_event(ws_client, ws_event)
        
        # Force ultra_nip reaction
        bot_event = {
            "type": "CHAT_MESSAGE",
            "user": "ultra_nip",
            "text": "GOAAAAALLL!! LIGHT IT UP! 🔥🔥🔥 RED SMOKE OVER THE PITCH!",
            "color": "#F43F5E",
            "time": "90:10"
        }
        await broadcast_event(ws_client, bot_event)
        print("[Footy Poller] Emitted test goal event successfully.")
        if ws_client:
            await ws_client.close()
        return

    # Run full match simulation
    await run_simulation(args.mock_match_id, ws_client)
    
    if ws_client:
        await ws_client.close()

if __name__ == "__main__":
    asyncio.run(main())
