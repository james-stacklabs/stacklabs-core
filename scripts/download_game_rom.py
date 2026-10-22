import requests
import json
import argparse
import os

def download_rom(game_pk):
    print(f"[*] Fetching MLB Feed for Game {game_pk}...")
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    res = requests.get(url)
    
    if res.status_code != 200:
        print("Failed to fetch game data.")
        return
        
    feed = res.json()
    allPlays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    gd_teams = feed.get("gameData", {}).get("teams", {})
    away_team = gd_teams.get("away", {}).get("abbreviation", "AWY")
    home_team = gd_teams.get("home", {}).get("abbreviation", "HME")
    
    rom_data = {
        "game_pk": game_pk,
        "away_team": away_team,
        "home_team": home_team,
        "plays": []
    }
    
    for play in allPlays:
        about = play.get("about", {})
        inning = f"{'Top' if about.get('isTopInning') else 'Bot'} {about.get('inning')}"
        desc = play.get("result", {}).get("description", "")
        if not desc: continue
        
        away_score = play.get("result", {}).get("awayScore", 0)
        home_score = play.get("result", {}).get("homeScore", 0)
        
        rom_data["plays"].append({
            "inning": inning,
            "desc": desc,
            "away_score": away_score,
            "home_score": home_score,
            "outs": play.get("count", {}).get("outs", 0),
            "balls": play.get("count", {}).get("balls", 0),
            "strikes": play.get("count", {}).get("strikes", 0),
            "pitcher": play.get("matchup", {}).get("pitcher", {}).get("fullName", ""),
            "batter": play.get("matchup", {}).get("batter", {}).get("fullName", "")
        })
        
    os.makedirs("/home/james/stacklabs/data/roms", exist_ok=True)
    rom_path = f"/home/james/stacklabs/data/roms/game_{game_pk}.json"
    
    with open(rom_path, 'w') as f:
        json.dump(rom_data, f, indent=4)
        
    print(f"[*] Game ROM created! Saved {len(rom_data['plays'])} plays to {rom_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download MLB Game as a FanStack ROM")
    parser.add_argument("--game_pk", required=True, help="MLB Game PK to download")
    args = parser.parse_args()
    download_rom(args.game_pk)
