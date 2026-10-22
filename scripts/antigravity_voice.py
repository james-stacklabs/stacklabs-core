import sys
import json
import asyncio
import websockets
import time
import os

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 antigravity_voice.py 'text to speak'")
        sys.exit(1)

    text = sys.argv[1]
    
    # 1. Send WebSocket message to trigger CypherCell
    try:
        async with websockets.connect("ws://127.0.0.1:8008") as ws:
            payload = {
                "type": "CHAT_MESSAGE",
                "is_penalty_box": False,
                "user": "Antigravity",
                "text": text,
                "channel": "vocal_matrix"
            }
            await ws.send(json.dumps(payload))
            print("Payload sent to CypherCell.")
    except Exception as e:
        print(f"WS Error: {e}")

    # 2. Write to Vocal Matrix payload files for browser TTS (both Dev & Prod paths)
    payload_paths = [
        "/home/james/stacklabs/01_Sovereign_Portal/public/tts-proxy/tts_payload.json",
        "/home/james/stacklabs/04_Sovereign_Core/tts_payload.json"
    ]
    
    tts_payload = {
        "id": str(int(time.time())),
        "text": text
    }
    
    for path in payload_paths:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(tts_payload, f)
            print(f"Payload written to {path}")
        except Exception as e:
            print(f"Error writing payload to {path}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
