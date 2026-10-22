import asyncio
import websockets
import json

async def listen():
    async with websockets.connect("ws://localhost:8008") as ws:
        async for message in ws:
            msg = json.loads(message)
            if msg.get("type") == "STATE_UPDATE" and msg.get("data", {}).get("pitcher"):
                print(message[:500])
                break

asyncio.run(listen())
