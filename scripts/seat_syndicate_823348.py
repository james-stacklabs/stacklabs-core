#!/usr/bin/env python3
"""
Seat 5 Prediction Market Syndicate Advocates + Pilot & MetsFan_86 into Game 823348 (NYM @ PIT)
Path: /home/james/stacklabs/scripts/seat_syndicate_823348.py
"""

import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
GAME_PK = "823348"

SYNDICATE_HANDLES = [
    "vegas_vinnie",
    "parlay_pete",
    "hedge_master_hank",
    "fade_frankie",
    "voodoo_valerie",
    "metsfan_86",
    "pilot_james",
    "james"
]

def main():
    print(f"[*] Seating Syndicate Advocates into Game Room {GAME_PK} (NYM @ PIT)...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Resolve personas
    resolved = []
    for uname in SYNDICATE_HANDLES:
        cur.execute("SELECT id, user_name, display_name FROM persona WHERE user_name = ? COLLATE NOCASE", (uname,))
        p_row = cur.fetchone()
        
        cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ? COLLATE NOCASE", (uname,))
        u_row = cur.fetchone()
        
        p_id = p_row[0] if p_row else (u_row[0] if u_row else None)
        if p_id:
            resolved.append((uname, p_id))
            print(f"  [+] Resolved @{uname} -> ID: {p_id}")
        else:
            print(f"  [!] Warning: @{uname} not found in database!")

    # 2. Seat each persona in game_persona and m2m_persona_room
    for uname, p_id in resolved:
        # Check game_persona
        cur.execute("SELECT id FROM game_persona WHERE game_pk = ? AND persona_id = ?", (GAME_PK, p_id))
        if not cur.fetchone():
            gp_id = str(uuid.uuid4()).replace('-', '')
            cur.execute("""
                INSERT INTO game_persona (id, game_pk, persona_id, seat_state)
                VALUES (?, ?, ?, 'active')
            """, (gp_id, GAME_PK, p_id))
            print(f"  [+] Added @{uname} to game_persona ({GAME_PK})")

        # Check m2m_persona_room
        cur.execute("SELECT sys_id FROM m2m_persona_room WHERE room = ? AND (persona = ? OR persona = ?)", (GAME_PK, p_id, uname))
        if not cur.fetchone():
            m2m_id = str(uuid.uuid4()).replace('-', '')
            cur.execute("""
                INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay)
                VALUES (?, ?, ?, ?)
            """, (m2m_id, p_id, GAME_PK, f"Deployed to Game {GAME_PK} (NYM vs PIT) - Syndicate Advocate"))
            print(f"  [+] Added @{uname} to m2m_persona_room ({GAME_PK})")

    # 3. Update active_game_rooms & mlb_schedule
    cur.execute("""
        INSERT OR REPLACE INTO active_game_rooms (game_id, url, home_team, away_team, status, date_scheduled)
        VALUES (?, ?, 'PIT', 'NYM', 'ACTIVE', '2026-08-08')
    """, (GAME_PK, f"mlb.com/gameday/mets-vs-pirates/2026/08/08/{GAME_PK}"))

    cur.execute("""
        UPDATE mlb_schedule
        SET room_state = 'active', status = 'In-Progress'
        WHERE game_pk = ?
    """, (GAME_PK,))

    # 4. Ensure fan_wallet records exist for all advocates
    for uname in ["vegas_vinnie", "parlay_pete", "hedge_master_hank", "fade_frankie", "voodoo_valerie", "metsfan_86", "james", "pilot_james"]:
        cur.execute("SELECT user_id FROM fan_wallet WHERE user_id = ?", (uname,))
        if not cur.fetchone():
            cur.execute("INSERT INTO fan_wallet (user_id, balance, lifetime_winnings) VALUES (?, 10000, 0)", (uname,))
            print(f"  [+] Provisioned 10,000 FanCredits for @{uname}")

    # 5. Create or verify game-specific Prediction Market for Game 823348
    market_id = f"mkt_{GAME_PK}_nym_pit"
    cur.execute("SELECT market_id FROM prediction_market WHERE market_id = ?", (market_id,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO prediction_market (market_id, advocate_id, prompt_text, status)
            VALUES (?, 'vegas_vinnie', 'NYM @ PIT: Will NY Mets score > 4.5 Runs tonight?', 'OPEN')
        """, (market_id,))
        
        cur.execute("INSERT INTO market_pool (pool_id, market_id, option_key, total_staked) VALUES (?, ?, 'YES', 500)", (f"pool_{market_id}_YES", market_id))
        cur.execute("INSERT INTO market_pool (pool_id, market_id, option_key, total_staked) VALUES (?, ?, 'NO', 500)", (f"pool_{market_id}_NO", market_id))
        print(f"  [+] Created prediction market {market_id} for NYM @ PIT")

    conn.commit()
    conn.close()
    print(f"[✔] Successfully seated all 5 Syndicate Advocates + Pilot & MetsFan_86 into Game {GAME_PK}!")

if __name__ == "__main__":
    main()
