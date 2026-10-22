import json
import sqlite3

json_path = "/home/james/stacklabs/dna/dropzone/daily_28042026/sovereign_ai_bots_export.json"
db_path = "/home/james/stacklabs/dna/sovereign_now.db"

with open(json_path, 'r') as f:
    personas = json.load(f)

conn = sqlite3.connect(db_path, timeout=10)
cursor = conn.cursor()

updated_count = 0

for p in personas:
    sys_id = p.get('sys_id')
    if not sys_id: continue
    
    # Update sys_user
    cursor.execute("""
        UPDATE sys_user 
        SET title = ?, introduction = ?
        WHERE sys_id = ?
    """, (p.get('title', ''), p.get('introduction', ''), sys_id))
    
    # Update cmdb_ci_ai_persona
    # Wait, does cmdb_ci_ai_persona share the same sys_id? Let's check cmdb_ci name.
    # Usually cmdb_ci.name == sys_user.user_name
    cursor.execute("SELECT sys_id FROM cmdb_ci WHERE name=?", (p.get('user_name'),))
    res = cursor.fetchone()
    if res:
        ci_sys_id = res[0]
        cursor.execute("""
            UPDATE cmdb_ci_ai_persona 
            SET u_system_prompt = ?
            WHERE sys_id = ?
        """, (p.get('u_system_prompt', ''), ci_sys_id))
        updated_count += 1

conn.commit()
print(f"Updated {updated_count} persona records successfully across both tables.")
conn.close()
