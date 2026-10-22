import asyncio
import websockets
import json
import sys

async def ignite():
    uri = "ws://127.0.0.1:8008/ws"
    print(f"[*] Connecting to {uri}...", flush=True)
    async with websockets.connect(uri) as ws:
        # Join room 823498
        await ws.send(json.dumps({"type": "JOIN_ROOM", "room": "823498", "target_game_pk": "823498"}))
        print("[+] Joined room 823498", flush=True)
        await asyncio.sleep(0.5)

        # Inject Subway Series pregame scenario
        payload = {
            "type": "update_context",
            "target_game_pk": "823498",
            "target_nodes": ["ALL"],
            "text": "[MAXIMUM SUBWAY SERIES RIVALRY SCENARIO: Pre-Game Warmups at Yankee Stadium. New York Mets (68-78) at New York Yankees (84-62). Nolan McLean (11-8, 3.06 ERA) vs Carlos Rodón (5-3, 3.09 ERA). First pitch in under 90 minutes. Mets fans: debate whether McLean split-finger can tame the short porch, Keith critiques outfield cutoff positioning, Barf complains about bullpen dread and overpriced Bronx beer. Yankees fans: flex 27 rings, Soto and Judge power, and Rodón striking out the side. Pure authentic New York sports talk!]"
        }
        await ws.send(json.dumps(payload))
        print("[+] Dispatched update_context payload to room 823498", flush=True)

        # Listen for generated responses for 10 seconds
        print("[*] Listening for incoming chatbot banter (10s window)...", flush=True)
        count = 0
        start_t = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_t < 10.0:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(raw)
                if data.get("type") == "CHAT_MESSAGE":
                    count += 1
                    user = data.get("user", "Unknown")
                    model = data.get("model_engine", "default")
                    text = data.get("text", "")
                    print(f"  [{count}] @{user} ({model}): {text}", flush=True)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"[-] Recv error: {e}", flush=True)
                break
        print(f"[*] Ignition sweep complete. Received {count} chat messages.", flush=True)

if __name__ == "__main__":
    asyncio.run(ignite())
