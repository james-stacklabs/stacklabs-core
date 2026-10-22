import sqlite3
import json
from datetime import datetime, timezone

with open('/home/james/sovereign_inbox/daily_05112026/fresh_bios.json', 'r') as f:
    data = json.load(f)

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
con = sqlite3.connect(db_path)
cur = con.cursor()

now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
updated_count = 0

def serialize(val):
    if isinstance(val, list): return '\n'.join([str(v) for v in val])
    if isinstance(val, dict): return json.dumps(val, indent=2)
    return str(val) if val else ''

for row in data:
    if not row or 'user_name' not in row: continue
    username = row['user_name']
    
    sp = serialize(row.get('system_prompt', ''))
    bn = serialize(row.get('behavior_notes', ''))
    gov = serialize(row.get('governance', ''))
    
    cur.execute("""
        UPDATE persona 
        SET system_prompt = ?, behavior_notes = ?, governance = ?, updated_at = ?
        WHERE user_name = ?
    """, (sp, bn, gov, now_str, username))
    
    if cur.rowcount > 0:
        updated_count += 1

con.commit()
con.close()
print(f"Applied updates to {updated_count} personas.")
