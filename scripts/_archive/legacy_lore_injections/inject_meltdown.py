import asyncio
import websockets
import json

async def trigger():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            payload = {
                "type": "update_context",
                "text": "[POSTGAME CHAOS: The Philadelphia Phillies have officially lost! This marks their THIRD HOME SERIES LOSS of the year already. The season is completely unraveling at Citizens Bank Park! Fans are furious.]",
                "target_nodes": ["ALL", "823477"],
                "target_game_pk": "823477"
            }
            await ws.send(json.dumps(payload))
            print("🚀 MARD Engine Payload Injected: Post-Game Series Loss Alert on Port 8008!")

            # Fire a Wardy broadcast to instigate
            wardy_payload = {
                "type": "broadcast",
                "message": "And that is the ballgame! An 11-2 absolute annihilation here at Citizens Bank Park! And folks, it gets worse... that is the THIRD home series the Phillies have lost already this year! The boos are raining down. Is this team already broken?! What a total disaster in South Philly!"
            }
            await asyncio.sleep(2)
            await ws.send(json.dumps(wardy_payload))
            print("🎙️ Wardy Instigation Sent")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
