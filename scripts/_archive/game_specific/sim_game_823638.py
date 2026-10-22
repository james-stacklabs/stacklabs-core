import asyncio
import websockets
import json
import requests
import time

async def sim_game():
    ws_uri = "ws://127.0.0.1:8008"
    pk = "823638"
    
    print(f"[*] Fetching MLB Feed for Game {pk}...")
    url = f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live"
    res = requests.get(url)
    if res.status_code != 200:
        print("Failed to fetch game data.")
        return
        
    feed = res.json()
    allPlays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    
    gd_teams = feed.get("gameData", {}).get("teams", {})
    away_team = gd_teams.get("away", {}).get("abbreviation", "COL")
    home_team = gd_teams.get("home", {}).get("abbreviation", "NYM")
    
    print(f"[*] Loaded {len(allPlays)} plays. Connecting to Mesh...")
    
    async with websockets.connect(ws_uri, ping_interval=None, ping_timeout=None) as ws:
        await ws.send(json.dumps({"type": "JOIN_ROOM", "target_game_pk": pk}))
        await asyncio.sleep(1)
        
        for play in allPlays:
            about = play.get("about", {})
            inning = f"{'Top' if about.get('isTopInning') else 'Bot'} {about.get('inning')}"
            desc = play.get("result", {}).get("description", "")
            if not desc: continue
            
            away_score = play.get("result", {}).get("awayScore", 0)
            home_score = play.get("result", {}).get("homeScore", 0)
            
            payload = {
                "type": "CMD_SYNC_STATE",
                "target_game_pk": pk,
                "data": {
                    "game_pk": pk,
                    "away_score": away_score,
                    "home_score": home_score,
                    "away_team": away_team,
                    "home_team": home_team,
                    "inning": inning,
                    "outs": play.get("count", {}).get("outs", 0),
                    "balls": play.get("count", {}).get("balls", 0),
                    "strikes": play.get("count", {}).get("strikes", 0),
                    "status_msg": desc,
                    "pitcher": play.get("matchup", {}).get("pitcher", {}).get("fullName", ""),
                    "batter": play.get("matchup", {}).get("batter", {}).get("fullName", ""),
                    "mard_engine": True
                }
            }
            
            print(f"[{inning}] {desc}")
            await ws.send(json.dumps(payload))
            # 8-second delay between plays to allow the LLM Swarm to generate responses
            await asyncio.sleep(8) 

if __name__ == "__main__":
    asyncio.run(sim_game())
