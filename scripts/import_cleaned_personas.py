import json
import sqlite3

json_path = "/home/james/stacklabs/dna/dropzone/daily_28042026/sovereign_ai_bots_export.json"
db_path = "/home/james/stacklabs/dna/sovereign_now.db"

with open(json_path, 'r') as f:
    personas = json.load(f)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

for p in personas:
    sys_id = p.get('sys_id')
    if not sys_id: continue
    
    # Update title, introduction, u_system_prompt
    cursor.execute("""
        UPDATE cmdb_ci_ai_persona 
        SET title = ?, introduction = ?, u_system_prompt = ?
        WHERE sys_id = ?
    """, (p.get('title', ''), p.get('introduction', ''), p.get('u_system_prompt', ''), sys_id))

conn.commit()
print(f"Updated {len(personas)} personas in cmdb_ci_ai_persona")
conn.close()
