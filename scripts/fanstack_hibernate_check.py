#!/home/james/stacklabs/.venv/bin/python3
# =============================================================================
# SOVEREIGN OS — AUTOMATED FANSTACK HIBERNATION SCRIPT
# Version: 1.0 (Stealth Ground-Truth Check)
# Reference: STRY8791004
#
# SDLC INVARIANTS:
#   • Enforces SQLite Write-Ahead Logging (WAL) concurrency protocol (KI-045).
#   • Preserves core databases and control interfaces.
#   • Surgical execution via stop_fanstack.sh.
# =============================================================================

import sys
import os
import requests
import sqlite3
import subprocess
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

def check_and_hibernate():
    db_path = '/home/james/stacklabs/dna/sovereign_now.db'
    if not os.path.exists(db_path):
        print(f"[{datetime.now().isoformat()}] Database not found at {db_path}", file=sys.stderr)
        return
        
    conn = sqlite3.connect(db_path)
    # Configure WAL mode as per KI-045
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    
    # Determine the baseball gameday date (Eastern Time)
    now_et = datetime.now(ZoneInfo('America/New_York'))
    if now_et.hour < 10:
        target_date = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        target_date = now_et.strftime('%Y-%m-%d')
        
    print(f"[{datetime.now().isoformat()}] Checking game status for target date: {target_date}")
    
    # Query mlb_schedule for games scheduled on target_date
    cursor.execute("""
        SELECT game_pk, home_team, away_team, status
        FROM mlb_schedule
        WHERE game_date = ?
    """, (target_date,))
    games = cursor.fetchall()
    conn.close()
    
    if not games:
        print(f"[{datetime.now().isoformat()}] No games scheduled for {target_date}. Initiating hibernation...")
        run_shutdown()
        return

    active_games = []
    for game_pk, home_team, away_team, db_status in games:
        try:
            url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                status_code = data['gameData']['status']['statusCode']
                # In Progress (I), Pregame (P), Scheduled (S), Warmup (W) are active states
                if status_code in ['I', 'P', 'S', 'W']:
                    active_games.append(f"{away_team}@{home_team} (PK: {game_pk}, status: {status_code})")
            else:
                # If StatsAPI is unreachable, check DB status fallback
                if db_status in ['I', 'P', 'S', 'W', 'staged', 'pregame', 'active']:
                    active_games.append(f"{away_team}@{home_team} (PK: {game_pk}, db_fallback: {db_status})")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Error checking game {game_pk}: {e}", file=sys.stderr)
            if db_status in ['I', 'P', 'S', 'W', 'staged', 'pregame', 'active']:
                active_games.append(f"{away_team}@{home_team} (PK: {game_pk}, db_fallback_err: {db_status})")

    if active_games:
        print(f"[{datetime.now().isoformat()}] Active games remaining on {target_date}: {', '.join(active_games)}. Hibernation aborted.")
    else:
        print(f"[{datetime.now().isoformat()}] All games for {target_date} are completed. Initiating hibernation...")
        run_shutdown()

def run_shutdown():
    shutdown_script = "/home/james/stacklabs/scripts/stop_fanstack.sh"
    if not os.path.exists(shutdown_script):
        print(f"[{datetime.now().isoformat()}] Shutdown script not found at {shutdown_script}", file=sys.stderr)
        return
        
    print(f"[{datetime.now().isoformat()}] Executing {shutdown_script}...")
    res = subprocess.run(["/bin/bash", shutdown_script], capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    print(f"[{datetime.now().isoformat()}] Hibernation completed with exit code {res.returncode}")

if __name__ == "__main__":
    check_and_hibernate()
