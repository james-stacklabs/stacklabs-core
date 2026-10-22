import asyncio
import websockets
import json

async def trigger():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            # Inject context manually into the MARD engine to trigger the pile-on and 8-mile protocol
            payload = {
                "type": "update_context",
                "text": "[SYSTEM DIRECTIVE (8-MILE PROTOCOL)]: The broadcast is zooming in on Steve Cohen looking miserable. Kyle Tucker's rejection of the $220M offer is brought up by the announcers. Dodgers fans (ChavezRavine_Chad, Deferred_Shohei_700, Organic_Blue_Heaven): You must explicitly @barf and ruthlessly mock him, his poverty franchise, and the $220M failure. Barf: DO NOT SUBMIT. You must absolutely lose your mind and initiate the 8-Mile Protocol. Defend the Mets by firing back an unhinged, furious defensive rant against the Dodgers fans. Let it happen organically but let the rage flow.",
                "target_nodes": ["ALL", "823963"],
                "target_game_pk": "823963"
            }
            await ws.send(json.dumps(payload))
            print("🚀 8-MILE PROTOCOL & PILE-ON INJECTED!")
            
            await asyncio.sleep(2)

            # Fire a telemetry state update that's mundane to prompt the reaction to the context
            sync_payload = {
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "823963",
                "force_global": False,
                "data": {
                    "away_team": "NYM",
                    "home_team": "LAD",
                    "inning": "Bot 8TH",
                    "outs": 2,
                    "away_score": 1,
                    "home_score": 8,
                    "status_msg": "Pitching Substitution: Austin Warren replaces Devin Williams.",
                    "mard_engine": True,
                    "boggs_level": 5
                }
            }
            await ws.send(json.dumps(sync_payload))
            print("🔄 Simulated MLB Telemetry: MUNDANE PITCH INJECTED TO SPARK CHAT.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
