import asyncio
import websockets
import json

async def trigger():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            # 1. Update Context Payload
            payload = {
                "type": "update_context",
                "text": "[MAXIMUM SCENARIO: The New York Yankees have just WALKED OFF the Los Angeles Angels! Incredible victory! The stadium is going berserk! Yankees fans, react with pure unhinged euphoria! Angels fans, react with absolute heartbreak and rage!]",
                "target_nodes": ["ALL", "823561"],
                "target_game_pk": "823561"
            }
            await ws.send(json.dumps(payload))
            print("🚀 MARD Engine Payload Injected: NYY Walk-Off Alert!")

            await asyncio.sleep(1)

            # 2. Fire a Wardy broadcast to instigate
            wardy_payload = {
                "type": "broadcast",
                "message": "OH MY GOODNESS! DO YOU BELIEVE IT?! The Yankees have walked off the Angels in absolutely dramatic fashion! This place is shaking! What a disastrous, heartbreaking loss for the Angels bullpen! The Bronx is burning with hype tonight!"
            }
            await ws.send(json.dumps(wardy_payload))
            print("🎙️ Wardy Instigation Sent")
            
            await asyncio.sleep(1)

            # 3. Fire a final telemetry state update to seal the UI
            sync_payload = {
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "823561",
                "force_global": False,
                "data": {
                    "away_team": "LAA",
                    "home_team": "NYY",
                    "inning": "Bot 9TH",
                    "outs": 2,
                    "status_msg": "Yankees walk off the Angels! Final Score.",
                    "mard_engine": True,
                    "boggs_level": 5
                }
            }
            await ws.send(json.dumps(sync_payload))
            print("🔄 Simulated MLB Telemetry Match End")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
