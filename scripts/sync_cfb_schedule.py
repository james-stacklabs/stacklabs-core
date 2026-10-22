#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: COLLEGE FOOTBALL (CFB) SCHEDULE SYNC DAEMON
# Path: /home/james/stacklabs/scripts/sync_cfb_schedule.py
# SDLC Ticket: WO0010082-CFB-SCHEDULE-AND-TELEMETRY-INGRESS
# Subsystem: 19_Sovereign_Sports / 15_FanStack
# Description: Syncs NCAA FBS College Football schedules into the canonical
#              sport_schedule database table with sport='CFB'.
# ==============================================================================

import sys
import os
import datetime
import logging
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

# Set up module path and database helper
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from core.db import get_db
except ImportError:
    from scripts.core.db import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [CFB_SYNC] %(message)s"
)
logger = logging.getLogger("cfb_sync")

ESPN_CFB_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"


def parse_cfb_event(ev: Dict[str, Any], date_str: str) -> Optional[Dict[str, Any]]:
    """Parse a single ESPN CFB event object into a normalized dictionary."""
    try:
        game_pk = str(ev.get("id"))
        name = ev.get("name", "")
        status_detail = ev.get("status", {}).get("type", {}).get("detail", "Scheduled")
        
        competitions = ev.get("competitions", [{}])
        if not competitions:
            return None
        comp = competitions[0]
        
        venue_name = comp.get("venue", {}).get("fullName", "College Football Stadium")
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
            
        competitors = comp.get("competitors", [])
        home_comp = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away_comp = next((c for c in competitors if c.get("homeAway") == "away"), {})
        
        home_team = home_comp.get("team", {}).get("abbreviation") or home_comp.get("team", {}).get("location", "HOME")
        away_team = away_comp.get("team", {}).get("abbreviation") or away_comp.get("team", {}).get("location", "AWAY")
        
        home_score = int(home_comp.get("score", 0)) if home_comp.get("score") else 0
        away_score = int(away_comp.get("score", 0)) if away_comp.get("score") else 0
        
        # Extract Top 25 ranks (99 indicates unranked)
        home_rank = home_comp.get("curatedRank", {}).get("current", 99)
        away_rank = away_comp.get("curatedRank", {}).get("current", 99)
        is_ranked_matchup = (home_rank < 99) or (away_rank < 99)

        status_info = ev.get("status", {}).get("type", {})
        status_detail = status_info.get("detail", "Scheduled")
        status_state = status_info.get("state", "pre")
        completed = status_info.get("completed", False)
        
        is_live = (status_state == "in") or ("Quarter" in status_detail) or ("Half" in status_detail) or ("OT" in status_detail and not completed)
        is_final = completed or ("Final" in status_detail)
        room_state = "active" if is_live else ("completed" if is_final else "staged")

        return {
            "game_pk": game_pk,
            "name": name,
            "game_date": game_date,
            "game_time": game_time_str,
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "home_rank": home_rank,
            "away_rank": away_rank,
            "is_ranked": is_ranked_matchup,
            "venue": venue_name,
            "status": status_detail,
            "room_state": room_state,
        }
    except Exception as e:
        logger.error(f"Error parsing event {ev.get('id')}: {e}", exc_info=True)
        return None


def sync_cfb_date(date_str: str, top25_only: bool = False) -> int:
    """Sync CFB games for a specific YYYYMMDD date from ESPN API (FBS Division I)."""
    formatted_date = date_str.replace("-", "")
    # groups=80 limits query strictly to FBS Division I games
    url = f"{ESPN_CFB_SCOREBOARD_URL}?dates={formatted_date}&groups=80"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            logger.warning(f"ESPN API returned HTTP {r.status_code} for date {date_str}")
            return 0
        data = r.json()
        events = data.get("events", [])
        
        count = 0
        with get_db() as conn:
            cur = conn.cursor()
            for ev in events:
                parsed = parse_cfb_event(ev, date_str)
                if not parsed:
                    continue
                
                if top25_only and not parsed["is_ranked"]:
                    continue
                
                # Format team labels with rank badge if applicable
                home_label = f"#{parsed['home_rank']} {parsed['home_team']}" if parsed['home_rank'] < 99 else parsed['home_team']
                away_label = f"#{parsed['away_rank']} {parsed['away_team']}" if parsed['away_rank'] < 99 else parsed['away_team']
                
                cur.execute("""
                    INSERT INTO sport_schedule (
                        game_pk, sport, game_date, game_time, home_team, away_team,
                        home_score, away_score, current_status, venue, status,
                        room_state, boggs_level, sim_speed, sys_updated_on
                    ) VALUES (
                        ?, 'CFB', ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, 3, 1.0, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT(game_pk) DO UPDATE SET
                        game_date = excluded.game_date,
                        game_time = excluded.game_time,
                        home_team = excluded.home_team,
                        away_team = excluded.away_team,
                        home_score = excluded.home_score,
                        away_score = excluded.away_score,
                        current_status = excluded.current_status,
                        venue = excluded.venue,
                        status = excluded.status,
                        room_state = excluded.room_state,
                        sys_updated_on = CURRENT_TIMESTAMP
                """, (
                    parsed["game_pk"], parsed["game_date"], parsed["game_time"],
                    home_label, away_label,
                    parsed["home_score"], parsed["away_score"], parsed["status"],
                    parsed["venue"], parsed["status"],
                    parsed["room_state"]
                ))
                count += 1
                logger.info(f"🏈 Synced CFB Game: {parsed['game_pk']} | {away_label} ({parsed['away_score']}) @ {home_label} ({parsed['home_score']}) [{parsed['status']}] (state={parsed['room_state']})")
                
            conn.commit()
        return count
    except Exception as e:
        logger.error(f"Error syncing CFB date {date_str}: {e}", exc_info=True)
        return 0


def main():
    logger.info("🏈 [CFB SCHEDULE SYNC] Querying ESPN FBS Scoreboard...")
    dates_to_sync = []
    top25_only = "--top25" in sys.argv
    
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    
    if args:
        for arg in args:
            dates_to_sync.append(arg.replace("-", ""))
    else:
        # Default: Sync today and next 3 days (Thursday - Sunday college weekend)
        today = datetime.date.today()
        for i in range(4):
            d = today + datetime.timedelta(days=i)
            dates_to_sync.append(d.strftime("%Y%m%d"))
            
    total_synced = 0
    for d in dates_to_sync:
        logger.info(f"📅 Fetching FBS slate for {d} (Top 25 Filter: {top25_only})...")
        synced = sync_cfb_date(d, top25_only=top25_only)
        total_synced += synced
        
    logger.info(f"✅ [CFB SYNC COMPLETE] Total {total_synced} College Football games synced to sport_schedule.")


if __name__ == "__main__":
    main()
