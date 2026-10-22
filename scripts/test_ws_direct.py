import asyncio
import websockets
import json

async def send_chat():
    uri = "ws://localhost:8008"
    async with websockets.connect(uri) as ws:
        # Join room 2026082201
        await ws.send(json.dumps({"type": "JOIN_ROOM", "target_game_pk": "2026082201"}))
        await asyncio.sleep(0.5)

        # Send test chat message
        payload = {
            "type": "CHAT_MESSAGE",
            "user": "james (Pilot)",
            "color": "#3B82F6",
            "text": "Yo Puke and Barf, respond to this message right now!",
            "target_game_pk": "2026082201"
        }
        print(f"Sending message: {payload}")
        await ws.send(json.dumps(payload))

        # Listen for 15 seconds for replies
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < 15:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(msg)
                if data.get("type") == "CHAT_MESSAGE":
                    print(f"RECEIVED CHAT REPLY: [{data.get('user')}] {data.get('text')}")
            except asyncio.TimeoutError:
                pass

if __name__ == "__main__":
    asyncio.run(send_chat())
