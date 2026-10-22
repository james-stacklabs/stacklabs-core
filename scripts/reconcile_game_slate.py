#!/usr/bin/env python3
"""
reconcile_game_slate.py
=======================
Dynamically reconciles stale game rooms in sovereign_now.db, cleans past game
seats, and sets active stream to today's live marquee game (Mets flagship matchup).
"""

import sqlite3
import uuid
import requests
import json
import os
import sys
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def get_current_slate_date() -> str:
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.hour < 4:
        return (now_et - timedelta(days=1)).strftime("%Y-%m-%d")
    return now_et.strftime("%Y-%m-%d")

def main():
    print("🚀 [GAME SLATE RECONCILER] Starting dynamic database reconciliation...")
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    cur = conn.cursor()

    target_date = get_current_slate_date()
    if len(sys.argv) > 1 and sys.argv[1].startswith("202"):
        target_date = sys.argv[1]

    print(f"📅 Target Slate Date: {target_date}")

    # 1. Find today's marquee Mets game
    cur.execute("""
        SELECT game_pk, home_team, away_team, status, room_state
        FROM sport_schedule
        WHERE game_date = ? AND (home_team = 'NYM' OR away_team = 'NYM')
        ORDER BY game_time ASC LIMIT 1
    """, (target_date,))
    today_mets_row = cur.fetchone()
    
    today_mets_game = str(today_mets_row['game_pk']) if today_mets_row else None
    home_team = today_mets_row['home_team'] if today_mets_row else 'NYM'
    away_team = today_mets_row['away_team'] if today_mets_row else 'HOU'

    # Find yesterday's game to cleanly swap
    cur.execute("""
        SELECT game_pk FROM sport_schedule
        WHERE game_date < ? AND (home_team = 'NYM' OR away_team = 'NYM')
        ORDER BY game_date DESC, game_time DESC LIMIT 1
    """, (target_date,))
    yest_row = cur.fetchone()
    yesterday_mets_game = str(yest_row['game_pk']) if yest_row else None

    print(f"🧹 1. Deactivating all past MLB game rooms prior to {target_date}...")
    cur.execute("UPDATE sport_schedule SET room_state = 'staged' WHERE game_date < ? AND sport = 'MLB'", (target_date,))
    if yesterday_mets_game:
        cur.execute("UPDATE sport_schedule SET room_state = 'staged', status = 'Final' WHERE game_pk = ?", (yesterday_mets_game,))
        cur.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'staged' WHERE game_pk = ?", (yesterday_mets_game,))
        cur.execute("UPDATE active_game_rooms SET status = 'CLOSED' WHERE game_id = ?", (yesterday_mets_game,))
        cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (yesterday_mets_game,))
        cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (yesterday_mets_game,))

    cur.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'staged' WHERE game_pk IN (SELECT game_pk FROM sport_schedule WHERE game_date < ? AND sport = 'MLB')", (target_date,))
    cur.execute("UPDATE active_game_rooms SET status = 'CLOSED' WHERE date_scheduled < ? AND (game_id LIKE '82%' OR game_id NOT LIKE '4018%')", (target_date,))

    if today_mets_game:
        print(f"⚾ 2. Activating today's live Mets matchup ({today_mets_game}: {away_team} @ {home_team})...")
        cur.execute("UPDATE sport_schedule SET room_state = 'active', status = 'Live', home_score = 0, away_score = 0 WHERE game_pk = ?", (today_mets_game,))
        cur.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'active' WHERE game_pk = ?", (today_mets_game,))
        cur.execute("""
            INSERT OR REPLACE INTO active_game_rooms (game_id, url, home_team, away_team, status, date_scheduled, sys_updated_on)
            VALUES (?, ?, ?, ?, 'ACTIVE', ?, CURRENT_TIMESTAMP)
        """, (today_mets_game, f"/stream/{today_mets_game}", home_team, away_team, target_date))

        print(f"👥 3. Seating curated advocates for room {today_mets_game}...")
        cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (today_mets_game,))
        cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (today_mets_game,))

        # Seating pool (Purged placeholder @dot and @statcast_daytrader per WO0010172)
        nym_users = ['barf', 'unclesteviestan', 'keith_fanboy', '7_train_terry']
        
        # Look up opponent personas dynamically
        opp_team = away_team if home_team == 'NYM' else home_team
        if opp_team == 'BAL':
            opp_users = ['birdland_boomer', 'dirty_water_danny']
        else:
            cur.execute("SELECT user_name FROM persona WHERE team = ? OR team = ? COLLATE NOCASE LIMIT 4", (opp_team, opp_team.lower()))
            opp_users = [r['user_name'] for r in cur.fetchall()]
            if not opp_users:
                opp_users = ['houston_crush', 'space_city_sam']

        all_users = nym_users + opp_users
        for uname in all_users:
            cur.execute("SELECT sys_user.sys_id, persona.id FROM sys_user LEFT JOIN persona ON sys_user.user_name = persona.user_name WHERE sys_user.user_name = ? COLLATE NOCASE", (uname,))
            row = cur.fetchone()
            if row:
                user_sys_id = row['sys_id']
                persona_id = row['id'] if row['id'] else user_sys_id
                
                gp_id = str(uuid.uuid4()).replace('-', '')
                cur.execute("INSERT INTO game_persona (id, game_pk, persona_id, seat_state) VALUES (?, ?, ?, 'active')",
                            (gp_id, today_mets_game, persona_id))
                
                m2m_id = str(uuid.uuid4()).replace('-', '')
                cur.execute("INSERT INTO m2m_persona_room (sys_id, persona, room) VALUES (?, ?, ?)",
                            (m2m_id, uname, today_mets_game))
                
                cur.execute("UPDATE sys_user SET active = 1 WHERE sys_id = ?", (user_sys_id,))
                print(f"  ✓ Seated @{uname} in room {today_mets_game}")

    conn.commit()
    conn.close()
    print("✅ Database reconciliation committed successfully.")

    if today_mets_game:
        print("\n🔄 4. Hot-swapping active stream on Port 8000 via REST API...")
        try:
            res = requests.post("http://127.0.0.1:8000/api/session/swap-stream", json={
                "target_game_pk": today_mets_game,
                "previous_game_pk": yesterday_mets_game or today_mets_game,
                "bring_gang": False
            }, timeout=5)
            print("  Swap stream response:", res.json())
        except Exception as e:
            print("  Warning: failed to hot-swap stream via REST:", e)

    print("\n🔍 5. Verifying active session...")
    try:
        res = requests.get("http://127.0.0.1:8000/api/session/active-stream", timeout=5)
        print("  Active stream:", res.json())
    except Exception as e:
        print("  Warning: failed to get active stream:", e)

    print("\n🔍 6. Verifying /api/sports/active_games on Port 8097...")
    try:
        res = requests.get("http://127.0.0.1:8097/api/sports/active_games", timeout=5)
        games = res.json()
        print(f"  Total active games on TV Wall: {len(games)}")
    except Exception as e:
        print("  Warning: failed to get active games from 8097:", e)

if __name__ == "__main__":
    main()
