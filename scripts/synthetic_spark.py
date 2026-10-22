import asyncio
import websockets
import json

async def trigger():
    uri = "ws://localhost:8008"
    async with websockets.connect(uri) as ws:
        payload = {
            "type": "update_context",
            "text": "SYNTHETIC: The gates at Citi Field are officially open. You are in your seats pregaming. You have hot dogs, you have beer, and you are actively discussing the pregame news. Someone bring up the Yankees 17-inning scoreless streak immediately. Do not wait for a pitch."
        }
        await ws.send(json.dumps(payload))
        
        # We also trigger an event to force the bot logic
        event = {
            "type": "trigger_event",
            "event": "brawl"
        }
        await ws.send(json.dumps(event))
        
        print("Sent SYNTHETIC spark to start chat!")

asyncio.run(trigger())
