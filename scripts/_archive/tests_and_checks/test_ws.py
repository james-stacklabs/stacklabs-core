import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://127.0.0.1:8008") as ws:
        await ws.send(json.dumps({
            "type": "hot_take_rant",
            "persona": "barf",
            "topic": "The MLB implementing 'Robot Umpires'",
            "engine_override": "gemini-1.5-flash",
            "target_game_pk": "hot_takes"
        }))
        print("Sent rant request. Waiting for response...")
        for _ in range(5):
            msg = await ws.recv()
            print("Received:", msg)

asyncio.run(test())
