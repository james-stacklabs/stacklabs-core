import sqlite3
import uuid

db = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
c = db.cursor()

# Find game_pk for Mets vs Athletics
c.execute("SELECT game_pk, name FROM cmdb_ci_fanstack_room WHERE name LIKE '%Mets%' AND name LIKE '%Athletics%'")
room = c.fetchone()
if not room:
    print("Could not find Mets/A's game!")
    exit(1)
game_pk = room[0]
room_name = room[1]
print(f"Target game_pk: {game_pk} ({room_name})")

# Banish Shohei Ghost
c.execute("UPDATE cmdb_ci_ai_persona SET u_deployment_zone = 'BENCHED' WHERE sys_id IN (SELECT sys_id FROM sys_user WHERE user_name = 'shohei_ghost')")
c.execute("DELETE FROM m2m_persona_room WHERE persona = 'shohei_ghost'")
print("shohei_ghost banished to BENCHED.")

# explicit map for A's fans
as_fans = ['coliseum_ghost', 'possum_protector', 'sacramento_skeptic', 'vegas_void_voter']
for fan in as_fans:
    # Update deployment zone
    c.execute("UPDATE cmdb_ci_ai_persona SET u_deployment_zone = ? WHERE sys_id IN (SELECT sys_id FROM sys_user WHERE user_name = ?)", (game_pk, fan))
    
    # Ensure they are in the m2m_persona_room mapping correctly
    # Delete existing map just in case
    c.execute("DELETE FROM m2m_persona_room WHERE persona = ?", (fan,))
    prompt_overlay = f"Current Matchup Context: Deployed to {room_name}."
    m2m_sys_id = str(uuid.uuid4()).replace('-', '')
    c.execute("INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?, ?, ?, ?)", (m2m_sys_id, fan, game_pk, prompt_overlay))

db.commit()
db.close()
print("Athletics fans successfully deployed.")
