#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: NFL SCHEDULE SYNC DAEMON (ESPN SCOREBOARD API)
# Script: /home/james/stacklabs/scripts/sync_nfl_schedule.py
# SDLC: ENHC2026082002
# Description: Syncs NFL schedules (Preseason, Regular Season, Postseason)
#              into the canonical sport_schedule database table with sport='NFL'.
# ==============================================================================
import requests
import sqlite3
import datetime
import sys
import os
from zoneinfo import ZoneInfo

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

ESPN_NFL_TEAMS = {
    "1": "ATL", "2": "BUF", "3": "CHI", "4": "CIN", "5": "CLE", "6": "DAL",
    "7": "DEN", "8": "DET", "9": "GB", "10": "TEN", "11": "IND", "12": "KC",
    "13": "LV", "14": "LAR", "15": "MIA", "16": "MIN", "17": "NE", "18": "NO",
    "19": "NYG", "20": "NYJ", "21": "PHI", "22": "ARI", "23": "PIT", "24": "LAC",
    "25": "SF", "26": "SEA", "27": "TB", "28": "WSH", "29": "CAR", "30": "JAX",
    "33": "BAL", "34": "HOU"
}

def sync_nfl_date(date_str: str, conn: sqlite3.Connection) -> int:
    """Sync NFL games for a specific YYYYMMDD date from ESPN API."""
    formatted_date = date_str.replace("-", "")
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={formatted_date}"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"⚠️ ESPN API error for date {date_str}: HTTP {r.status_code}")
            return 0
        data = r.json()
        events = data.get("events", [])
        
        cur = conn.cursor()
        count = 0
        
        for ev in events:
            game_pk = str(ev.get("id"))
            name = ev.get("name", "")
            status_detail = ev.get("status", {}).get("type", {}).get("detail", "Scheduled")
            
            competitions = ev.get("competitions", [{}])[0]
            venue_name = competitions.get("venue", {}).get("fullName", "NFL Stadium")
            game_time_str = ev.get("date", "")
            
            # Parse ISO date converted to America/New_York local date
            game_date = None
            if game_time_str:
                try:
                    utc_dt = datetime.datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
                    eastern_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))
                    game_date = eastern_dt.strftime("%Y-%m-%d")
                except Exception:
                    game_date = game_time_str[:10]
            if not game_date:
                game_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str
            
            competitors = competitions.get("competitors", [])
            home_comp = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away_comp = next((c for c in competitors if c.get("homeAway") == "away"), {})
            
            home_abbr = home_comp.get("team", {}).get("abbreviation") or ESPN_NFL_TEAMS.get(str(home_comp.get("id")), "HOME")
            away_abbr = away_comp.get("team", {}).get("abbreviation") or ESPN_NFL_TEAMS.get(str(away_comp.get("id")), "AWAY")
            
            # Upsert into sport_schedule with sport='NFL'
            cur.execute("""
                INSERT OR REPLACE INTO sport_schedule (
                    game_pk, sport, game_date, game_time, home_team, away_team,
                    venue, status, room_state, boggs_level, sim_speed, sys_updated_on
                ) VALUES (
                    ?, 'NFL', ?, ?, ?, ?,
                    ?, ?, 
                    COALESCE((SELECT room_state FROM sport_schedule WHERE game_pk = ?), 'staged'),
                    COALESCE((SELECT boggs_level FROM sport_schedule WHERE game_pk = ?), 3),
                    1.0, CURRENT_TIMESTAMP
                )
            """, (
                game_pk, game_date, game_time_str, home_abbr, away_abbr,
                venue_name, status_detail, game_pk, game_pk
            ))
            count += 1
            print(f"  🏈 Synced NFL Game: {game_pk} | {away_abbr} @ {home_abbr} ({name}) | {status_detail}")
            
        conn.commit()
        return count
    except Exception as e:
        print(f"❌ Error syncing NFL date {date_str}: {e}")
        return 0

def main():
    print("🏈 [NFL SCHEDULE SYNC] Querying ESPN NFL Scoreboard...")
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    
    dates_to_sync = []
    
    if len(sys.argv) > 1 and sys.argv[1] != "--today":
        # Custom dates passed
        for arg in sys.argv[1:]:
            dates_to_sync.append(arg.replace("-", ""))
    else:
        # Default: Sync today and next 3 days (covering full weekend slate)
        today = datetime.date.today()
        for i in range(4):
            d = today + datetime.timedelta(days=i)
            dates_to_sync.append(d.strftime("%Y%m%d"))
            
    total_synced = 0
    for d in dates_to_sync:
        print(f"\n📅 Fetching slate for {d}...")
        synced = sync_nfl_date(d, conn)
        total_synced += synced
        
    conn.close()
    print(f"\n✅ [NFL SYNC COMPLETE] Total {total_synced} NFL games synced to sport_schedule.")

if __name__ == "__main__":
    main()
