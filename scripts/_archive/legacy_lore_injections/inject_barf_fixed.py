import asyncio
import websockets
import json

async def trigger():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            # 1. Provide a CMD_SYNC_STATE so the relay populates game_states
            # and broadcasts a STATE_UPDATE to un-stick the UI and trigger ambient mode.
            sync_payload = {
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "823965",
                "force_global": False,
                "data": {
                    "away_team": "NYM",
                    "home_team": "LAD",
                    "inning": "Pre",
                    "outs": 0,
                    "away_score": 0,
                    "home_score": 0,
                    "status_msg": "Pre-Game Warmups",
                    "mard_engine": True,
                    "boggs_level": 5
                }
            }
            await ws.send(json.dumps(sync_payload))
            print("🚀 MARD Engine Payload Injected: CMD_SYNC_STATE for 823965!")

            await asyncio.sleep(2)
            
            # Fire it again a few seconds later to Ensure Ambient Entropy Interval Triggers
            # The bots use a random timer, so providing multiple ticks forces the loop
            sync_payload["data"]["status_msg"] = "Pre-Game Warmups."
            await ws.send(json.dumps(sync_payload))
            print("🔄 Forced Second Ambient Tick for Barf")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
