import asyncio
import websockets
import json

async def test_recv():
    uri = "ws://localhost:8008"
    async with websockets.connect(uri) as ws:
        print("Connected to port 8008!")
        await ws.send(json.dumps({"type": "JOIN_ROOM", "room": "2026082201", "target_game_pk": "2026082201"}))
        for _ in range(5):
            msg = await ws.recv()
            print("RECV:", msg[:200])

if __name__ == "__main__":
    asyncio.run(test_recv())
