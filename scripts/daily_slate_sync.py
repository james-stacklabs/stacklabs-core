#!/usr/bin/env python3
"""
daily_slate_sync.py
===================
Unified Daily Slate Synchronization Daemon for Sovereign Sports,
FanStack Watch Parties, and the Sports Bar TV Wall Matrix.

This script executes the complete daily game ingestion, schedule sync,
advocate seating, stream URL resolution, and room activation pipeline.
It is designed to run idempotently both interactively and as an automated
daily cron job at dawn (06:00 AM EDT) and midday.

Usage:
    python3 scripts/daily_slate_sync.py              # Full daily sync
    python3 scripts/daily_slate_sync.py --fast       # Fast sync (skip heavy lore gen)
    python3 scripts/daily_slate_sync.py --verify     # Verification pass only
"""

import os
import sys
import json
import sqlite3
import subprocess
import requests
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

SOVEREIGN_HOME = "/home/james/stacklabs"
VENV_PYTHON = os.path.join(SOVEREIGN_HOME, ".venv", "bin", "python3")
DB_PATH = os.path.join(SOVEREIGN_HOME, "dna", "sovereign_now.db")

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def get_current_slate_date() -> str:
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.hour < 4:
        from datetime import timedelta
        return (now_et - timedelta(days=1)).strftime("%Y-%m-%d")
    return now_et.strftime("%Y-%m-%d")

def run_step(name: str, cmd: list[str]) -> bool:
    log(f"▶️  Step: {name}")
    try:
        res = subprocess.run(cmd, cwd=SOVEREIGN_HOME, capture_output=True, text=True, timeout=120)
        if res.returncode == 0:
            log(f"  ✅ {name} completed successfully.")
            if res.stdout.strip():
                for line in res.stdout.strip().split("\n")[:4]:
                    log(f"     {line}")
            return True
        else:
            log(f"  ⚠️ {name} exited with code {res.returncode}: {res.stderr.strip()[:200]}")
            return False
    except Exception as e:
        log(f"  ❌ {name} failed with error: {e}")
        return False

def verify_active_games_api(slate_date: str) -> dict:
    log("🔍 Verifying /api/sports/active_games on Port 8097...")
    try:
        resp = requests.get("http://127.0.0.1:8097/api/sports/active_games", timeout=5)
        if resp.status_code == 200:
            games = resp.json()
            log(f"  ✅ Active Games Endpoint Online: {len(games)} games active across TV Wall.")
            mlb_games = [g for g in games if g.get("sport") == "MLB"]
            nfl_games = [g for g in games if g.get("sport") == "NFL"]
            log(f"     MLB: {len(mlb_games)} games | NFL: {len(nfl_games)} games")
            return {"status": "OK", "total": len(games), "mlb": len(mlb_games), "nfl": len(nfl_games)}
        else:
            log(f"  ⚠️ Endpoint returned status code: {resp.status_code}")
            return {"status": "WARN", "code": resp.status_code}
    except Exception as e:
        log(f"  ❌ Could not connect to Port 8097: {e}")
        return {"status": "ERROR", "error": str(e)}

def main():
    py_exec = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
    slate_date = get_current_slate_date()
    
    log("=" * 65)
    log(f"  SOVEREIGN SPORTS BAR TV SLATE DAILY SYNC")
    log(f"  Target Slate Date: {slate_date}")
    log("=" * 65)

    if "--verify" in sys.argv:
        verify_active_games_api(slate_date)
        return

    # 1. Ambient Lore & Promo Ingestion (Stage fresh news & promos before room setup)
    run_step(
        "Yardbarker Entropy Pump",
        [py_exec, os.path.join(SOVEREIGN_HOME, "scripts", "yardbarker_entropy_pump.py")]
    )
    run_step(
        "Gmail Promo Sweeper",
        [py_exec, os.path.join(SOVEREIGN_HOME, "scripts", "gmail_promo_sweeper.py")]
    )
    run_step(
        "MLB News Crawler (Context DB)",
        [py_exec, os.path.join(SOVEREIGN_HOME, "scripts", "mlb_news_crawler.py")]
    )

    # 2. Sync MLB & NFL Schedules
    run_step(
        "MLB Schedule Sync (StatsAPI)",
        [py_exec, os.path.join(SOVEREIGN_HOME, "scripts", "sync_mlb_schedule.py")]
    )
    run_step(
        "NFL Schedule Sync (ESPN)",
        [py_exec, os.path.join(SOVEREIGN_HOME, "scripts", "sync_nfl_schedule.py")]
    )

    # 3. Provision NFL Game Rooms & Seated Advocates
    run_step(
        "NFL Room Provisioning",
        [py_exec, os.path.join(SOVEREIGN_HOME, "scripts", "setup_nfl_rooms.py")]
    )

    # 4. Resolve Live Stream URLs (m3u8 / StreamEast / fallback)
    run_step(
        "Stream URL Resolver",
        [py_exec, os.path.join(SOVEREIGN_HOME, "scripts", "stream_url_resolver.py")]
    )

    # 5. Provision MLB Game Rooms, Personas & TMI Branches
    run_step(
        "MLB Room Provisioning & TMI Branches",
        [py_exec, os.path.join(SOVEREIGN_HOME, "scripts", "setup_all_rooms.py")]
    )

    # 6. Reconcile Dynamic Slate & Hot-Swap Active Stream
    run_step(
        "Dynamic Game Slate Reconciler",
        [py_exec, os.path.join(SOVEREIGN_HOME, "scripts", "reconcile_game_slate.py")]
    )

    # 7. Post-Sync Verification
    result = verify_active_games_api(slate_date)
    log("=" * 65)
    log(f"  SLATE SYNC FINISHED — TV WALL STATUS: {result.get('status')}")
    log("=" * 65)

if __name__ == "__main__":
    main()
