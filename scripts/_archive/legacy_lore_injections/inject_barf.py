import asyncio
import websockets
import json

async def trigger():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            # 1. Update Context just for Barf
            payload = {
                "type": "update_context",
                "text": "[ISOLATION CHAMBER: The walls are closing in. You are completely alone. WardyNYM is watching you. You are having an existential crisis about the Mets.]",
                "target_nodes": ["823965"],
                "target_game_pk": "823965"
            }
            await ws.send(json.dumps(payload))
            print("🚀 MARD Engine Payload Injected: Barf Isolation Context!")

            await asyncio.sleep(1)

            # 2. Fire a direct Wardy broadcast AT Barf
            wardy_payload = {
                "type": "CHAT_MESSAGE",
                "user": "WardyNYM",
                "persona": "WardyNYM",
                "color": "#f97316",
                "text": "BARF. Are you in there? It's Wardy. I'm broadcasting into your isolation chamber tonight. Prepare yourself. The doom is eternal.",
                "target_game_pk": "823965"
            }
            await ws.send(json.dumps(wardy_payload))
            print("🎙️ WardyNYM Teaser Sent to Game 823965")
            
            await asyncio.sleep(2)
            
            # 3. Fire an ambient trigger to make Barf respond
            ambient_trigger = {
                "type": "STATE_UPDATE",
                "target_game_pk": "823965",
                "data": {
                    "away_team": "NYM",
                    "home_team": "LAD",
                    "status_msg": "Scheduled",
                    "mard_engine": True,
                    "boggs_level": 5
                }
            }
            await ws.send(json.dumps(ambient_trigger))
            print("🔄 Forced Ambient Engine Tick for Barf")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
