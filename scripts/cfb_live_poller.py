#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: COLLEGE FOOTBALL (CFB) LIVE TELEMETRY POLLER
# Path: /home/james/stacklabs/scripts/cfb_live_poller.py
# SDLC Ticket: WO0010082-CFB-SCHEDULE-AND-TELEMETRY-INGRESS
# Subsystem: 19_Sovereign_Sports / 15_FanStack
# Description: Ingests real-time down/distance, drive charts, and play-by-play
#              telemetry from ESPN College Football summary into game_context.
# ==============================================================================

import sys
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

# Hoisted module path and database helper
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from core.db import get_db
except ImportError:
    from scripts.core.db import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [CFB_POLLER] %(message)s"
)
logger = logging.getLogger("cfb_poller")

ESPN_CFB_SUMMARY_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary"


def poll_cfb_game(event_id: str) -> Optional[Dict[str, Any]]:
    """Fetch and normalize live game summary for a specific CFB game event."""
    url = f"{ESPN_CFB_SUMMARY_BASE}?event={event_id}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            logger.warning(f"ESPN Summary API returned HTTP {r.status_code} for game {event_id}")
            return None
        data = r.json()
        
        header = data.get("header", {})
        competitions = header.get("competitions", [{}])
        if not competitions:
            return None
        comp = competitions[0]
        competitors = comp.get("competitors", [])
        
        home_comp = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away_comp = next((c for c in competitors if c.get("homeAway") == "away"), {})
        
        home_score = int(home_comp.get("score", 0)) if home_comp.get("score") else 0
        away_score = int(away_comp.get("score", 0)) if away_comp.get("score") else 0
        
        status_detail = comp.get("status", {}).get("type", {}).get("detail", "In Progress")
        
        # Current Drive & Play
        drives = data.get("drives", {})
        curr_drive = drives.get("current") or (drives.get("previous", [{}])[-1] if drives.get("previous") else {})
        plays = curr_drive.get("plays", [])
        last_play = plays[-1] if plays else {}
        
        play_text = last_play.get("text", "")
        down_dist = (
            last_play.get("end", {}).get("downDistanceText", "")
            or last_play.get("start", {}).get("downDistanceText", "")
            or ""
        )
        yardline = last_play.get("end", {}).get("yardLine", 50)
        possession_team = (
            last_play.get("start", {}).get("team", {}).get("id")
            or last_play.get("start", {}).get("possessionText")
        )
        
        # Boxscore team statistics
        boxscore = data.get("boxscore", {})
        teams_stats = boxscore.get("teams", [])
        away_stats = next((t for t in teams_stats if t.get("team", {}).get("id") == away_comp.get("id")), {})
        home_stats = next((t for t in teams_stats if t.get("team", {}).get("id") == home_comp.get("id")), {})
        
        def get_stat(stat_dict: Dict[str, Any], name: str) -> str:
            for s in stat_dict.get("statistics", []):
                if s.get("name") == name or s.get("label") == name:
                    return str(s.get("displayValue", "0"))
            return "0"

        return {
            "game_pk": event_id,
            "away_score": away_score,
            "home_score": home_score,
            "status": status_detail,
            "down_dist": down_dist,
            "yardline": yardline,
            "possession": possession_team,
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
        logger.error(f"Error polling game {event_id}: {e}", exc_info=True)
        return None


def update_game_telemetry(game_data: Dict[str, Any]) -> bool:
    """Persist normalized game telemetry into sport_schedule and game_context."""
    if not game_data or not game_data.get("game_pk"):
        return False
        
    game_pk = str(game_data["game_pk"])
    status = game_data.get("status", "In Progress")
    last_play = game_data.get("last_play", "").strip()
    down_dist = game_data.get("down_dist", "").strip() or "Down & Distance"

    try:
        with get_db() as conn:
            cur = conn.cursor()
            
            # 1. Update schedule status and live score
            cur.execute("""
                UPDATE sport_schedule 
                SET status = ?, 
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE game_pk = ?
            """, (status, game_pk))
            
            # 2. Inject latest play to game_context if novel
            if last_play:
                # Check for duplicate play to avoid spamming the log table
                cur.execute("""
                    SELECT content FROM game_context 
                    WHERE game_pk = ? AND source = 'espn_cfb' 
                    ORDER BY rowid DESC LIMIT 1
                """, (game_pk,))
                latest_row = cur.fetchone()
                last_recorded = latest_row["content"] if latest_row else None
                
                if last_recorded != last_play:
                    cur.execute("""
                        INSERT INTO game_context 
                            (id, game_pk, source, headline, content, tags, injected_at, sys_created_on)
                        VALUES (
                            lower(hex(randomblob(16))),
                            ?,
                            'espn_cfb',
                            ?,
                            ?,
                            'CFB,PLAY',
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP
                        )
                    """, (game_pk, down_dist, last_play))
                    logger.info(f"🎙️ [CFB INGRESS] Injected Play ({game_pk}): {down_dist} -> {last_play[:80]}...")
            
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Database error updating CFB telemetry for {game_pk}: {e}", exc_info=True)
        return False


def get_active_cfb_games() -> List[str]:
    """Retrieve list of active or scheduled CFB game_pks to poll."""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT game_pk FROM sport_schedule 
                WHERE sport = 'CFB' AND room_state IN ('active', 'staged')
                ORDER BY sys_updated_on DESC LIMIT 10
            """)
            rows = cur.fetchall()
            if rows:
                return [str(r["game_pk"]) for r in rows]
    except Exception as e:
        logger.error(f"Error querying active CFB games: {e}", exc_info=True)
    return []


def main():
    game_ids = sys.argv[1:] if len(sys.argv) > 1 else get_active_cfb_games()
    logger.info(f"🏈 [CFB POLLER] Target Games: {game_ids}")
    
    if not game_ids:
        logger.warning("No active CFB games found in sport_schedule. Run sync_cfb_schedule.py first.")
        return

    for gid in game_ids:
        telemetry = poll_cfb_game(gid)
        if telemetry:
            logger.info(
                f"🏈 {gid}: Score {telemetry['away_score']}-{telemetry['home_score']} | "
                f"{telemetry['status']} | {telemetry['down_dist']}: {telemetry['last_play'][:60]}"
            )
            update_game_telemetry(telemetry)
        else:
            logger.info(f"🏈 {gid}: Pre-Game or no live play stream available.")


if __name__ == "__main__":
    main()
