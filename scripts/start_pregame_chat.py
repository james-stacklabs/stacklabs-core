import asyncio
import websockets
import json

async def send_state():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            payload = {
                "type": "update_context",
                "text": "[MAXIMUM SCENARIO: Pre-Game Predictions. Tomorrow is April 21. The New York Mets are heading to Miami to play the Marlins. Everyone start intensely arguing, making highly specific and unhinged predictions for tomorrow's game! Drop exact scores, weird anomalies, and trash talk the Marlins!]",
                "target_game_pk": "MIA_PREGAME_001",
                "target_nodes": ["ALL"]
            }
            await ws.send(json.dumps(payload))
            print("Successfully injected start pregame context.")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(send_state())
