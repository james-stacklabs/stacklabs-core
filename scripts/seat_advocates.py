#!/usr/bin/env python3
# seat_advocates.py

import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
GAME_PK = "824428"

USERNAMES = [
    "bronx_bomber_bob",
    "pinstripe_purist",
    "bleacher_creature_99",
    "judgements_court",
    "believeland_rock",
    "cle_guardian_spirit",
    "midwest_scrappy",
    "jacobs_field_ghost",
    "barf",
    "unclesteviestan",
    "keith_fanboy",
    "wordy_nym",
    "2008_ghost",
    "fredbird_fiend",
    "arch_madness",
    "salsa_wizard",
    "dot",
    "pilot_james",
    "coach_shrubbs"
]

def main():
    print(f"[*] Seating exactly 19 advocates for game room {GAME_PK}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Find persona IDs from sys_user table to ensure correct JOIN keys
    persona_ids = []
    for uname in USERNAMES:
        cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ? COLLATE NOCASE", (uname,))
        row = cur.fetchone()
        if row:
            persona_ids.append((uname, row[0]))
        else:
            print(f"  [!] Persona username {uname} not found in sys_user table!")

    # Verify count
    print(f"[*] Resolved {len(persona_ids)}/19 personas from the database.")
    if len(persona_ids) < 19:
        print("[!] Warning: Did not resolve all 19 personas!")

    # Delete existing seats
    cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (GAME_PK,))
    cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (GAME_PK,))

    # Insert seats
    for uname, p_id in persona_ids:
        # Game persona seat
        gp_uuid = str(uuid.uuid4()).replace('-', '')
        cur.execute("""
            INSERT INTO game_persona (id, game_pk, persona_id, seat_state)
            VALUES (?, ?, ?, 'active')
        """, (gp_uuid, GAME_PK, p_id))

        # m2m persona room entry
        m2m_uuid = str(uuid.uuid4()).replace('-', '')
        cur.execute("""
            INSERT INTO m2m_persona_room (sys_id, persona, room)
            VALUES (?, ?, ?)
        """, (m2m_uuid, p_id, GAME_PK))
        
        print(f"  [+] Seated {uname} (ID: {p_id})")

    # Set status of game room to ACTIVE in active_game_rooms
    cur.execute("""
        INSERT OR REPLACE INTO active_game_rooms (game_id, url, home_team, away_team, status, date_scheduled)
        VALUES (?, ?, 'CLE', 'NYY', 'ACTIVE', '2026-06-10')
    """, (GAME_PK, f"mlb.com/gameday/yankees-vs-guardians/2026/06/10/{GAME_PK}"))

    conn.commit()
    conn.close()
    print("[✔] Seating complete.")

if __name__ == "__main__":
    main()
