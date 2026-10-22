import sqlite3
import uuid
import datetime

db = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
cursor = db.cursor()

personas = [
    'f23eba0639be4e10b2af6911efae2671',
    '6d3e44a07c03492784a9ffb80831f0f1',
    '4a8931cf7faa47be9f523ce44f86b92e'
]

games = [825088, 825089]
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for g in games:
    for p in personas:
        cursor.execute("SELECT 1 FROM game_persona WHERE game_pk=? AND persona_id=?", (g, p))
        if not cursor.fetchone():
            sys_id = uuid.uuid4().hex
            cursor.execute("INSERT INTO game_persona (id, game_pk, persona_id, joined_at, seat_state) VALUES (?, ?, ?, ?, 'active')", (sys_id, g, p, now))

db.commit()
db.close()
print("AZ Personas added")
