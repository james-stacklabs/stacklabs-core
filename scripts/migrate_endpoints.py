import os

relay_path = '/home/james/stacklabs/scripts/fanstack_relay.py'
core_path = '/home/james/stacklabs/scripts/sovereign_core_api.py'

with open(relay_path, 'r') as f:
    relay_lines = f.readlines()

new_relay_lines = []
extracted_lines = []

# Define line ranges to extract (1-indexed, inclusive)
# Found via previous analysis:
# sys_rules: 488-498
# system/start|pause|stop: 880-934
# cmdb_ci* & teams: 935-1294
# generic now/table: 1530-1640

ranges_to_extract = [
    (488, 498),
    (880, 934),
    (935, 1294),
    (1530, 1640)
]

def in_range(line_num):
    for start, end in ranges_to_extract:
        if start <= line_num <= end:
            return True
    return False

for i, line in enumerate(relay_lines, 1):
    if in_range(i):
        extracted_lines.append(line)
    else:
        new_relay_lines.append(line)

# Add our new PUT /api/sys_rules/{sys_id} endpoint logic to the extracted lines
extra_sys_rule_code = """
import json

class SysRuleUpdate(BaseModel):
    summary: str
    content: str

@fastapi_app.put("/api/sys_rules/{sys_id}")
async def update_sys_rule(sys_id: str, payload: SysRuleUpdate):
    \"\"\"Two-way sync: Update rule in DB and IDE Knowledge Directory.\"\"\"
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT rule_id FROM sys_rules WHERE sys_id=?", (sys_id,))
    row = cur.fetchone()
    if not row:
        con.close()
        raise HTTPException(status_code=404, detail="Rule not found")
        
    rule_id = row['rule_id']
    
    cur.execute("UPDATE sys_rules SET summary=?, content=?, sys_updated_on=CURRENT_TIMESTAMP WHERE sys_id=?", 
                (payload.summary, payload.content, sys_id))
    con.commit()
    con.close()
    
    # Write back to IDE Knowledge Base
    base_dir = f"/home/james/.gemini/antigravity/knowledge/{rule_id}"
    meta_path = os.path.join(base_dir, "metadata.json")
    rule_path = os.path.join(base_dir, "artifacts", "rule.md")
    
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        meta['summary'] = payload.summary
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)
            
    if os.path.exists(rule_path):
        with open(rule_path, 'w') as f:
            f.write(payload.content)
            
    return {"status": "success", "sys_id": sys_id, "rule_id": rule_id}
"""

with open(relay_path, 'w') as f:
    f.writelines(new_relay_lines)

with open(core_path, 'a') as f:
    f.write("\n\n# --- MIGRATED FROM FANSTACK RELAY ---\n")
    f.write("bot_process = None\ntelemetry_process = None\n\n")
    f.writelines(extracted_lines)
    f.write(extra_sys_rule_code)

print("Migration completed.")
