#!/usr/bin/env python3
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

# Roster of 28 eclectic, high-potency advocates for the "Come One, Come All" watch party
ROSTER = [
    "barf",
    "7_train_terry",
    "UncleStevieStan",
    "bartman",
    "ivy_inspector_ian",
    "CubsConspiracy",
    "bartmans_ghost",
    "wordy_nym",
    "dr_kosmos",
    "wavy",
    "senora",
    "420_linda",
    "pizzabot_74",
    "warden_barb",
    "cary_sterling",
    "vesper_vance",
    "mando_enforcer",
    "battery_chucker_jr",
    "Gaslamp_Goon",
    "pancho_scholar",
    "isolated_silo",
    "tomahawk",
    "the_chop_shop",
    "waffle_house_warrior",
    "dot",
    "skyline_chili_chad",
    "steamboat_stan",
    "keith_fanboy"
]

# The three active rooms tonight:
# 1. 823611 - Chicago Cubs @ New York Mets (In Progress)
# 2. 823284 - Atlanta Braves @ San Diego Padres (In Progress)
# 3. 823208 - Oakland Athletics @ San Francisco Giants (Pre-Game / Upcoming)
TARGET_GAMES = ["823611", "823284", "823208"]

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 30000;")
    cursor = conn.cursor()

    print(f"🚀 Deploying 'Come One, Come All' Watch Party for tonight's games: {TARGET_GAMES}...")

    for game_pk in TARGET_GAMES:
        print(f"\n🏟️ Seating roster in room {game_pk}...")
        
        # 1. Activate the room on the dashboard and schedule
        cursor.execute("""
            UPDATE cmdb_ci_fanstack_room 
            SET room_state = 'active', boggs_level = 3 
            WHERE game_pk = ?
        """, (game_pk,))

        cursor.execute("""
            UPDATE mlb_schedule
            SET room_state = 'active', boggs_level = 3
            WHERE game_pk = ?
        """, (game_pk,))

        # 2. Clear out legacy seating for this room to avoid duplicate constraints
        cursor.execute("DELETE FROM m2m_persona_room WHERE room = ?", (game_pk,))
        cursor.execute("DELETE FROM game_persona WHERE game_pk = ?", (game_pk,))

        # 3. Seat all advocates in both tables
        for username in ROSTER:
            cursor.execute("SELECT id FROM persona WHERE user_name = ?", (username,))
            row = cursor.fetchone()
            if not row:
                print(f"⚠️ Warning: Advocate '{username}' is missing from database. Skipping.")
                continue
            persona_id = row[0]

            # Seat in m2m_persona_room (modern room membership)
            m2m_id = uuid.uuid4().hex
            cursor.execute("""
                INSERT OR REPLACE INTO m2m_persona_room (sys_id, persona, room, prompt_overlay)
                VALUES (?, ?, ?, ?)
            """, (m2m_id, persona_id, game_pk, f"Come One, Come All: Seated inside Game ID {game_pk}."))

            # Seat in game_persona (relational seat map)
            gp_id = uuid.uuid4().hex
            cursor.execute("""
                INSERT OR REPLACE INTO game_persona (id, game_pk, persona_id, seat_state)
                VALUES (?, ?, ?, 'active')
            """, (gp_id, game_pk, persona_id))

            print(f"  ✅ Seated @{username}")

    conn.commit()
    conn.close()
    print("\n🏆 Successfully completed 'Come One, Come All' seeder deployment!")

if __name__ == "__main__":
    main()
