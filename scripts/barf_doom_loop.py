import asyncio
import websockets
import json
import random

async def loop():
    prompts = [
        "React to Senga's ERA ballooning to 7.07.",
        "Complain about the fact that Lindor and Semien are hitting sub-.200.",
        "Lament about the darkness of the universe and how the Mets are proof of cosmic suffering.",
        "Talk about how an 0-8 skid is just the beginning of a 162-game funeral.",
        "Mention that Francisco Alvarez is the only Met who actually brought a bat to the stadium."
    ]
    
    # Send the initial payload first
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            payload = {
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "824693",
                "force_global": False,
                "data": {
                    "away_team": "NYM",
                    "home_team": "CHC",
                    "inning": "Pre",
                    "outs": 0,
                    "away_score": 0,
                    "home_score": 0,
                    "status_msg": "Pre-Game Warmups",
                    "mard_engine": True,
                    "boggs_level": 5
                }
            }
            await ws.send(json.dumps(payload))
            print("🚀 MARD Engine Payload Injected: CMD_SYNC_STATE for 824693!")
    except Exception as e:
        print(f"Initial setup failed: {e}")

    await asyncio.sleep(2)
    
    while True:
        try:
            p = random.choice(prompts)
            update_payload = {
                "type": "update_context",
                "text": p,
                "target_game_pk": "824693",
                "target_nodes": ["barf"]
            }
            async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
                await ws.send(json.dumps(update_payload))
                print(f"Injected Doom Context: {p}")
        except Exception as e:
            print(f"Error during injection: {e}")
            
        # Wait 60-120 seconds between rants
        delay = random.randint(60, 120)
        await asyncio.sleep(delay)

if __name__ == "__main__":
    asyncio.run(loop())
