import asyncio
import websockets
import json
import time

async def trigger():
    try:
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            # 1. Pitch 1: Ball
            print("Sending Pitch 1... (Ball)")
            await ws.send(json.dumps({
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "823963",
                "data": {
                    "away_team": "NYM", "home_team": "LAD",
                    "inning": "Top 9TH", "outs": 2,
                    "away_score": 2, "home_score": 8,
                    "balls": 1, "strikes": 0,
                    "pitch_name": "Changeup", "pitch_speed": "88.0",
                    "batter": "Carson Benge", "pitcher": "Kyle Hurt",
                    "status_msg": "Kyle Hurt throws an 88.0 mph Changeup for a ball."
                }
            }))
            await asyncio.sleep(4)

            # 2. Pitch 2: Foul
            print("Sending Pitch 2... (Foul)")
            await ws.send(json.dumps({
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "823963",
                "data": {
                    "away_team": "NYM", "home_team": "LAD",
                    "inning": "Top 9TH", "outs": 2,
                    "away_score": 2, "home_score": 8,
                    "balls": 1, "strikes": 1,
                    "pitch_name": "Four-Seam Fastball", "pitch_speed": "96.6",
                    "batter": "Carson Benge", "pitcher": "Kyle Hurt",
                    "status_msg": "Kyle Hurt throws a 96.6 mph Fastball. Foul ball."
                }
            }))
            await asyncio.sleep(5)

            # 3. Inject Boggs 5 and 8-mile override manually to prime the doomers
            print("Priming bots for defeat...")
            await ws.send(json.dumps({
                "type": "update_context",
                "text": "[SYSTEM DIRECTIVE (TUCKER FALLOUT + LOSS)]: The Mets are 1 pitch away from an 8-2 loss and extending their losing streak to 9. The camera pans to Steve Cohen visibly shaking his head in the owner's box. The broadcast overtly mentions Kyle Tucker turning down the $220M contract earlier today. Barf: DO NOT HOLD BACK. Let the misery flow. Dodgers fans: Point and laugh.",
                "target_game_pk": "823963"
            }))
            await asyncio.sleep(2)

            # 4. Pitch 3: Strikeout swinging!
            print("Sending Final Pitch... (Game Over)")
            await ws.send(json.dumps({
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "823963",
                "data": {
                    "away_team": "NYM", "home_team": "LAD",
                    "inning": "Top 9TH", "outs": 3,
                    "away_score": 2, "home_score": 8,
                    "balls": 1, "strikes": 2,
                    "pitch_name": "Sinker", "pitch_speed": "94.2",
                    "batter": "Carson Benge", "pitcher": "Kyle Hurt",
                    "status_msg": "Carson Benge strikes out swinging. That's the ballgame. The Mets fall to the Dodgers 8-2, extending their dismal losing streak.",
                    "boggs_level": 5
                }
            }))
            print("Game Over Simulated!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
