#!/usr/bin/env python3
"""
seed_weedstack_room.py
Sets up the WEEDSTACK_SIM_001 game/room in the database and seats all 9 personas.
"""
import sqlite3, uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ROOM_KEY = "WEEDSTACK_SIM_001"

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL;")
cur = conn.cursor()

# 1. Clean old references
cur.execute("DELETE FROM mlb_schedule WHERE game_pk = ?", (ROOM_KEY,))
cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (ROOM_KEY,))

# 2. Insert active room schedule
cur.execute("""
    INSERT INTO mlb_schedule 
        (game_pk, game_date, home_team, away_team, venue, status, room_state, boggs_level, sim_speed)
    VALUES (?, datetime('now'), 'WEEDSTACK', 'WEEDSTACK', 'The Green Room', 'In Progress', 'active', 2, 1.0)
""", (ROOM_KEY,))

# 3. Retrieve WeedStack personas
cur.execute("SELECT id, user_name FROM persona WHERE team = 'WEEDSTACK'")
personas = cur.fetchall()

if not personas:
    print("⚠️ No WeedStack personas found in the database. Please run seed_weedstack_personas.py first.")
    conn.close()
    exit(1)

# 4. Seat them
for pid, user_name in personas:
    cur.execute("""
        INSERT INTO game_persona 
            (id, game_pk, persona_id, overlay, seat_state)
        VALUES (?, ?, ?, ?, 'active')
    """, (uuid.uuid4().hex, ROOM_KEY, pid, "React strictly to live WeedStack events and discussions."))
    print(f"Seated {user_name} in {ROOM_KEY}")

conn.commit()
conn.close()
print("✅ Seeding of room WEEDSTACK_SIM_001 complete.")
