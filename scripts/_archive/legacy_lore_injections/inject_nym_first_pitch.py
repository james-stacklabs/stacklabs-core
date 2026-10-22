import asyncio
import websockets
import json

async def trigger():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            # 1. Update Context Payload (First Pitch)
            payload = {
                "type": "update_context",
                "text": "[MAXIMUM SCENARIO: The first pitch has just been thrown in Los Angeles. The late West Coast game is underway! Mets fans, start spiraling about how long the night is going to be! Dodgers fans, arrive late and complain about the traffic!]",
                "target_nodes": ["ALL", "823963"],
                "target_game_pk": "823963"
            }
            await ws.send(json.dumps(payload))
            print("🚀 MARD Engine Payload Injected: First Pitch Alert!")

            await asyncio.sleep(1)

            # 2. Fire telemetry state update
            sync_payload = {
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "823963",
                "force_global": False,
                "data": {
                    "away_team": "NYM",
                    "home_team": "LAD",
                    "inning": "Top 1ST",
                    "outs": 0,
                    "status_msg": "PLAY BALL! First pitch thrown by Shohei Ohtani.",
                    "mard_engine": True,
                    "boggs_level": 4
                }
            }
            await ws.send(json.dumps(sync_payload))
            print("🔄 Simulated MLB Telemetry: Top 1st")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
