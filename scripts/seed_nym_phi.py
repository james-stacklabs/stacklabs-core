import sqlite3
import uuid
import datetime

db_path = "/home/james/stacklabs/dna/sovereign_now.db"

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all NYM and PHI personas
cursor.execute("SELECT id, user_name, team FROM persona WHERE team IN ('NYM', 'PHI')")
home_away_personas = cursor.fetchall()

# Specific guest personas
guest_names = [
    'senora', 
    'water_barrel_wayne', 
    'The Gambler', 
    'flavor_fanatic', 
    'jukebox_jesse', 
    'spiteful_sal', 
    'catnip_greta', 
    'bt4991_believer', 
    'structural_underhook', 
    'kayfabe_evangelist'
]

placeholders = ', '.join('?' for _ in guest_names)
cursor.execute(f"SELECT id, user_name, team FROM persona WHERE user_name IN ({placeholders})", guest_names)
guest_personas = cursor.fetchall()

all_seating = []
seen_ids = set()

# Combine lists
for p in home_away_personas + guest_personas:
    p_id, username, team = p
    if p_id not in seen_ids:
        seen_ids.add(p_id)
        all_seating.append((p_id, username, team))

game_pk = '823609'
prompt_overlay = f"Current Matchup Context: Deployed to Game {game_pk} (PHI @ NYM)."
now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Delete existing for this game room
cursor.execute("DELETE FROM m2m_persona_room WHERE room = ?", (game_pk,))
deleted_count = cursor.rowcount
print(f"Cleared {deleted_count} existing seating entries for room {game_pk}")

# Insert new entries
inserted_count = 0
for p_id, username, team in all_seating:
    sys_id = uuid.uuid4().hex
    cursor.execute(
        "INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay, sys_created_on, sys_updated_on) VALUES (?, ?, ?, ?, ?, ?)",
        (sys_id, p_id, game_pk, prompt_overlay, now_str, now_str)
    )
    inserted_count += 1
    print(f"Seated {username} ({team}) in room {game_pk}")

conn.commit()
conn.close()

print(f"Successfully seeded {inserted_count} advocates into room {game_pk}")
