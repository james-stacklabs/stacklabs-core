#!/usr/bin/env python3
import asyncio
import json
import sys
import urllib.request
import websockets

RELAY_WS_URL = "ws://127.0.0.1:8008"

def get_active_game_pk():
    if len(sys.argv) > 1:
        return sys.argv[1]
    try:
        req = urllib.request.Request("http://127.0.0.1:8097/api/sports/active_games", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 0:
                return str(data[0].get("game_pk", "823955"))
    except Exception as e:
        print(f"Error querying active game via REST API: {e}")
    return "823955"

async def main():
    game_pk = get_active_game_pk()
    if not game_pk:
        print("No active game room found in database. Exiting.")
        sys.exit(1)

    print(f"Targeting active game room: {game_pk}")

    sit_down_payload = {
        "type": "CMD_SIT_DOWN",
        "media_url": "/media/Keith_thrusts_arm__GO_SIT_202606201553.mp4",
        "sprite_url": "/media/go_sit_down_keith_fanboy_transparent.png",
        "duration_ms": 4500,
        "game_pk": game_pk
    }

    try:
        async with websockets.connect(RELAY_WS_URL) as ws:
            # Join the room first (standard protocol in relay)
            join_msg = {
                "type": "JOIN_ROOM",
                "target_game_pk": game_pk,
                "room": game_pk
            }
            await ws.send(json.dumps(join_msg))
            print(f"Sent JOIN_ROOM message for game {game_pk}")
            await asyncio.sleep(0.5)

            # Send the takeover command
            await ws.send(json.dumps(sit_down_payload))
            print(f"Sent CMD_SIT_DOWN payload: {json.dumps(sit_down_payload, indent=2)}")
            print("Takeover overlay triggered successfully!")
    except Exception as ws_err:
        print(f"WebSocket communication error: {ws_err}")

if __name__ == "__main__":
    asyncio.run(main())
