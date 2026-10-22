import asyncio
import websockets
import json

async def trigger():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            # 1. Update Context
            context_text = "BREAKING NEWS: Francisco Lindor is out long-term with an injury. Ronny Mauricio has been called up to replace him. WardyNYM is absolutely devastated but trying to stay rational and analytical about the impact on the roster."
            payload = {
                "type": "update_context",
                "text": context_text,
                "target_nodes": ["823639"],
                "target_game_pk": "823639"
            }
            await ws.send(json.dumps(payload))
            print("🚀 MARD Engine Context Updated with Lindor Injury News for Mets game 823639")

            await asyncio.sleep(1)

            # 2. Fire a direct Wardy broadcast
            wardy_payload = {
                "type": "CHAT_MESSAGE",
                "user": "WardyNYM",
                "persona": "WardyNYM",
                "color": "#f97316",
                "text": "Guys, I just saw the news. Lindor is out long term. Mauricio is called up. This is a massive blow to the infield defense and lineup. I'm trying to run the projections on how we survive this stretch, but it's not looking good.",
                "target_game_pk": "823639"
            }
            await ws.send(json.dumps(wardy_payload))
            print("🎙️ WardyNYM News Broadcast Sent to Game 823639")
            
            await asyncio.sleep(2)
            
            # 3. Fire an ambient trigger to make other personas (like Barf) respond to Wardy's news
            ambient_trigger = {
                "type": "STATE_UPDATE",
                "target_game_pk": "823639",
                "data": {
                    "away_team": "MIN",
                    "home_team": "NYM",
                    "status_msg": "Pre-Game",
                    "mard_engine": True,
                    "boggs_level": 8
                }
            }
            await ws.send(json.dumps(ambient_trigger))
            print("🔄 Forced Ambient Engine Tick for Game 823639")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
