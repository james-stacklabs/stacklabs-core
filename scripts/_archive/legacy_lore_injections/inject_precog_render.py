import asyncio
import websockets
import json

async def trigger():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            # 1. Update Context Payload (Pre-Cog Render)
            payload = {
                "type": "update_context",
                "text": "[HAILO PRE-COG RENDER COMPLETE: Visual anomaly detected on /dev/video0. The Mets bullpen has catastrophically collapsed in the bottom of the 9th inning. Shohei Ohtani has launched a walk-off grand slam. The stadium is erupting. The Mets have lost their 8th straight game in pure misery.]",
                "target_nodes": ["ALL", "823963"],
                "target_game_pk": "823963"
            }
            await ws.send(json.dumps(payload))
            print("🚀 HAILO TENSOR CORES EXECUTED: Pre-Cog Misery Frame Injected!")

            await asyncio.sleep(2)

            # 2. Fire telemetry state update
            sync_payload = {
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "823963",
                "force_global": False,
                "data": {
                    "away_team": "NYM",
                    "home_team": "LAD",
                    "inning": "Bot 9TH",
                    "outs": 2,
                    "away_score": 4,
                    "home_score": 8,
                    "pitch_name": "Slider",
                    "pitch_speed": "84.2",
                    "status_msg": "Shohei Ohtani hits a walk-off grand slam (7) to center field. DODGERS WIN. FINAL.",
                    "mard_engine": True,
                    "boggs_level": 5
                }
            }
            await ws.send(json.dumps(sync_payload))
            print("🔄 Simulated MLB Telemetry: PITCH INJECTED.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
