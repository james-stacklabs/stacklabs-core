import asyncio
import websockets
import json

async def send_injection():
    uri = "ws://localhost:8000/ws"
    payload = {
        "type": "CHAT_MSG",
        "author": "PRODUCER",
        "text": "Argue about the failed A.J. Minter signing and how the stat department caught Ryan Helsley pitch-tipping instead of signing him.",
        "cross_talk": True
    }
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps(payload))
            print("Producer directive injected successfully.")
    except Exception as e:
        print(f"Failed to inject: {e}")

if __name__ == "__main__":
    asyncio.run(send_injection())
