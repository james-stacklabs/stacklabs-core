import asyncio
import websockets
import json
import time
import sys

async def trigger_barf_streak(game_pk):
    uri = 'ws://127.0.0.1:8008/ws'
    try:
        async with websockets.connect(uri) as ws:
            # 1. Inform the personas in the specific room so they react in chat
            local_msg = {
                "type": "update_context",
                "text": "🚨 SYSTEM MESH INJECTION: BatteryBarf has illegally jumped the outfield wall! He is running completely naked across the grass! Security is chasing him! Total chaos on the field!",
                "target_game_pk": str(game_pk)
            }
            await ws.send(json.dumps(local_msg))
            print(f"✅ Injected chat context to room {game_pk}")
            
            # 2. Inform the TMINewsDesk to log the anomaly for Video/VFX generation
            tmi_msg = {
                "type": "TMI_ANOMALY",
                "event": "Streaker (BatteryBarf) naked on field",
                "time": "Mid 5th",
                "persona": "BatteryBarf", 
                "format": "Format A (VFX/Lifelike)",
                "script": "A wild fan streaks across the field in front of the players. He is completely naked and screaming. Police are tackling him.",
                "prompt": "Lifelike action cam football baseball game footage. A deranged middle-aged man running buck naked across a baseball outfield while players watch in shock. He is chased by security.",
                "id": f"anom-{game_pk}-{int(time.time())}",
                "target_game_pk": "GLOBAL"
            }
            await ws.send(json.dumps(tmi_msg))
            print(f"✅ Injected TMI_ANOMALY to GLOBAL for News Desk parsing")
            
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else '824125'
    asyncio.run(trigger_barf_streak(target))
