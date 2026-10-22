import asyncio
import websockets
import json

async def send_state():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            payload = {
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "824693",
                "force_global": False,
                "data": {
                    "away_team": "NYM",
                    "home_team": "CHC",
                    "inning": "Pre",
                    "outs": 0,
                    "away_score": 0,
                    "home_score": 0,
                    "status_msg": "Pre-Game Warmups",
                    "mard_engine": True,
                    "boggs_level": 5
                }
            }
            await ws.send(json.dumps(payload))
            print("Successfully injected initial state payload.")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(send_state())
