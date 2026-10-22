import requests
import datetime
import json

def fetch_json(url):
    try:
        res = requests.get(url, timeout=10)
        return res.json() if res.status_code == 200 else None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def main():
    print("==================================================")
    print(" ⚾ OPERATION: RETRO-CAUSALITY TMI SCANNER ⚾")
    print("==================================================")
    
    # Get today's and yesterday's games
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    
    start_date = yesterday.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    
    schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={start_date}&endDate={end_date}"
    print(f"[*] Fetching schedule for {start_date} to {end_date}...")
    schedule_data = fetch_json(schedule_url)
    
    if not schedule_data:
        print("[-] Failed to fetch schedule.")
        return
        
    game_pks = []
    for d in schedule_data.get("dates", []):
        for g in d.get("games", []):
            game_pks.append((g["gamePk"], g.get("teams", {}).get("away", {}).get("team", {}).get("name", "AWY"), g.get("teams", {}).get("home", {}).get("team", {}).get("name", "HME")))
            
    print(f"[*] Found {len(game_pks)} games in window.")
    
    for pk, away, home in game_pks:
        feed_url = f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live"
        feed = fetch_json(feed_url)
        if not feed: continue
        
        all_plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
        
        # State trackers for this specific game
        blowout_state = 0 # tracks which threshold we've hit (0, 7, 10, 15)
        
        for play in all_plays:
            play_desc = play.get("result", {}).get("description", "")
            if not play_desc: continue
            
            away_score = play.get("result", {}).get("awayScore", 0)
            home_score = play.get("result", {}).get("homeScore", 0)
            inning = play.get("about", {}).get("halfInning", "") + " " + str(play.get("about", {}).get("inning", ""))
            
            l_desc = play_desc.lower()
            
            # Rule 1: Blowout Detection
            run_diff = abs(away_score - home_score)
            
            if run_diff >= 15 and blowout_state < 15:
                blowout_state = 15
                print(f"[TMI-BLOWOUT-15] Game {pk} ({away} @ {home}) | Inning {inning} | Score: {away_score}-{home_score}")
                print(f"   => Catalyst Play: {play_desc}")
            elif run_diff >= 10 and blowout_state < 10:
                blowout_state = 10
                print(f"[TMI-BLOWOUT-10] Game {pk} ({away} @ {home}) | Inning {inning} | Score: {away_score}-{home_score}")
                print(f"   => Catalyst Play: {play_desc}")
            elif run_diff >= 7 and blowout_state < 7:
                blowout_state = 7
                print(f"[TMI-BLOWOUT-07] Game {pk} ({away} @ {home}) | Inning {inning} | Score: {away_score}-{home_score}")
                print(f"   => Catalyst Play: {play_desc}")
                
            # Rule 2: Basic Catch-All (HRs, Weird stuff)
            is_hr = "homers" in l_desc or "home run" in l_desc or "grand slam" in l_desc
            is_weird = "eject" in l_desc or "balk" in l_desc or "review" in l_desc or "interfere" in l_desc or "injur" in l_desc or "brawl" in l_desc or "fight" in l_desc or "benches clear" in l_desc
            
            if is_weird:
                print(f"[TMI-ANOMALY] Game {pk} ({away} @ {home}) | Inning {inning} | {play_desc}")
                
if __name__ == "__main__":
    main()
