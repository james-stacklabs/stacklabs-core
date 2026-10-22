#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: NFL LIVE TELEMETRY POLLER (ESPN API INGRESS)
# File: /home/james/stacklabs/scripts/nfl_live_poller.py
# ==============================================================================
import requests
import sqlite3
import time
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def poll_game(event_id: str):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={event_id}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        
        header = data.get("header", {})
        competition = header.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])
        
        home_comp = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away_comp = next((c for c in competitors if c.get("homeAway") == "away"), {})
        
        home_score = int(home_comp.get("score", 0))
        away_score = int(away_comp.get("score", 0))
        
        status_detail = competition.get("status", {}).get("type", {}).get("detail", "In Progress")
        
        # Current Drive & Play
        drives = data.get("drives", {})
        curr_drive = drives.get("current") or (drives.get("previous", [{}])[-1] if drives.get("previous") else {})
        plays = curr_drive.get("plays", [])
        last_play = plays[-1] if plays else {}
        
        play_text = last_play.get("text", "")
        down_dist = last_play.get("end", {}).get("downDistanceText", "") or last_play.get("start", {}).get("downDistanceText", "")
        yardline = last_play.get("end", {}).get("yardLine", 50)
        possession_team = last_play.get("start", {}).get("team", {}).get("id")
        
        # Team stats
        boxscore = data.get("boxscore", {})
        teams_stats = boxscore.get("teams", [])
        away_stats = next((t for t in teams_stats if t.get("team", {}).get("id") == away_comp.get("id")), {})
        home_stats = next((t for t in teams_stats if t.get("team", {}).get("id") == home_comp.get("id")), {})
        
        def get_stat(stat_dict, name):
            for s in stat_dict.get("statistics", []):
                if s.get("name") == name or s.get("label") == name:
                    return s.get("displayValue")
            return "0"

        return {
            "game_pk": event_id,
            "away_score": away_score,
            "home_score": home_score,
            "status": status_detail,
            "down_dist": down_dist,
            "yardline": yardline,
            "last_play": play_text,
            "away_total_yards": get_stat(away_stats, "totalYards"),
            "home_total_yards": get_stat(home_stats, "totalYards"),
            "away_pass_yards": get_stat(away_stats, "netPassingYards"),
            "home_pass_yards": get_stat(home_stats, "netPassingYards"),
            "away_rush_yards": get_stat(away_stats, "rushingYards"),
            "home_rush_yards": get_stat(home_stats, "rushingYards"),
            "away_top": get_stat(away_stats, "possessionTime"),
            "home_top": get_stat(home_stats, "possessionTime"),
        }
    except Exception as e:
        print(f"Error polling {event_id}: {e}")
        return None

def update_db(game_data):
    if not game_data:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE sport_schedule 
            SET status = ?, sys_updated_on = datetime('now')
            WHERE game_pk = ?
        """, (game_data["status"], game_data["game_pk"]))
        
        # Inject live play context if last_play exists
        if game_data["last_play"]:
            cur.execute("""
                INSERT INTO game_context 
                    (id, game_pk, source, headline, content, tags, injected_at, sys_created_on)
                VALUES (lower(hex(randomblob(16))), ?, 'espn_nfl', ?, ?, 'NFL,PLAY', datetime('now'), datetime('now'))
            """, (game_data["game_pk"], game_data["down_dist"], game_data["last_play"]))
            
        conn.commit()
    except Exception as e:
        print(f"DB error: {e}")
    finally:
        conn.close()

def get_active_nfl_games():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT game_pk FROM sport_schedule WHERE sport = 'NFL' AND room_state = 'active'")
        rows = cur.fetchall()
        if rows:
            return [r[0] for r in rows]
    except Exception as e:
        print(f"Error fetching active NFL games: {e}")
    finally:
        conn.close()
    return ["401873286", "401873285"]

if __name__ == "__main__":
    game_ids = sys.argv[1:] if len(sys.argv) > 1 else get_active_nfl_games()
    print(f"🏈 [NFL POLLER] Polling NFL Games: {game_ids}")
    for gid in game_ids:
        res = poll_game(gid)
        if res:
            print(f"🏈 {gid}: Score {res['away_score']}-{res['home_score']} | {res['status']} | {res['down_dist']}: {res['last_play']}")
            update_db(res)
        else:
            print(f"🏈 {gid}: Pre-Game / No live play events yet.")
