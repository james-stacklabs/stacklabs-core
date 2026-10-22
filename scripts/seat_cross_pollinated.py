#!/usr/bin/env python3
# seat_cross_pollinated.py

import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
GAME_PK = "824428"

USERNAMES = [
    # Spite Slice
    "gyro_master",
    "pizzabot_74",
    "sconer_stoner",
    # WeedStack & Wild Seed
    "gummy_guru",
    "wild_seed_william",
    # Gonzas Store
    "gonza_snack_emperor",
    "counter_clerk_carl",
    # AetherVet & Wild Paws
    "telemetry_ted",
    "rescue_rita",
    # NYY & CLE
    "bronx_bomber_bob",
    "pinstripe_purist",
    "believeland_rock",
    "midwest_scrappy",
    # Main FanStack Core & PHI / STL
    "barf",
    "unclesteviestan",
    "fredbird_fiend",
    "2008_ghost",
    # Host
    "pilot_james"
]

def main():
    print(f"[*] Seating exactly 18 cross-pollinated advocates for game room {GAME_PK}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Find persona IDs from both tables to ensure correct mapping
    seating_records = []
    for uname in USERNAMES:
        # 1. Fetch persona ID from persona table (for game_persona)
        cur.execute("SELECT id FROM persona WHERE user_name = ? COLLATE NOCASE", (uname,))
        p_row = cur.fetchone()
        p_id = p_row[0] if p_row else None

        # 2. Fetch sys_id from sys_user table (for m2m_persona_room)
        cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ? COLLATE NOCASE", (uname,))
        u_row = cur.fetchone()
        u_id = u_row[0] if u_row else None

        if p_id and u_id:
            seating_records.append((uname, p_id, u_id))
        else:
            print(f"  [!] Persona username {uname} could not be resolved! (persona: {p_id}, sys_user: {u_id})")

    # Verify count
    print(f"[*] Resolved {len(seating_records)}/18 personas from the database.")
    if len(seating_records) != 18:
        print(f"[!] Warning: Did not resolve exactly 18 personas! Count: {len(seating_records)}")

    # Delete existing seats
    cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (GAME_PK,))
    cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (GAME_PK,))

    # Insert seats
    for uname, p_id, u_id in seating_records:
        # Game persona seat (uses persona.id)
        gp_uuid = str(uuid.uuid4()).replace('-', '')
        cur.execute("""
            INSERT INTO game_persona (id, game_pk, persona_id, seat_state)
            VALUES (?, ?, ?, 'active')
        """, (gp_uuid, GAME_PK, p_id))

        # m2m persona room entry (uses sys_user.sys_id)
        m2m_uuid = str(uuid.uuid4()).replace('-', '')
        cur.execute("""
            INSERT INTO m2m_persona_room (sys_id, persona, room)
            VALUES (?, ?, ?)
        """, (m2m_uuid, u_id, GAME_PK))
        
        print(f"  [+] Seated {uname} (game_persona: {p_id}, m2m: {u_id})")

    # Ensure status of game room to ACTIVE in active_game_rooms
    cur.execute("""
        INSERT OR REPLACE INTO active_game_rooms (game_id, url, home_team, away_team, status, date_scheduled)
        VALUES (?, ?, 'CLE', 'NYY', 'ACTIVE', '2026-06-10')
    """, (GAME_PK, f"mlb.com/gameday/yankees-vs-guardians/2026/06/10/{GAME_PK}"))

    conn.commit()
    conn.close()
    print("[✔] Cross-pollinated seating complete.")

if __name__ == "__main__":
    main()
