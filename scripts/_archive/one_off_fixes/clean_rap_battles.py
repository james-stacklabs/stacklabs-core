import sqlite3
import re

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
con = sqlite3.connect(db_path)
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute("SELECT id, system_prompt, behavior_notes, governance, deep_lore FROM persona").fetchall()
updated_count = 0

pattern = re.compile(r'(?i)(you are currently trapped in the SD vs COL 8-Mile rap battle override alongside other completely unhinged personas\.?|8-Mile rap battle|rap battle|override)')

for row in rows:
    pid = row['id']
    sp = row['system_prompt'] or ''
    bn = row['behavior_notes'] or ''
    gov = row['governance'] or ''
    dl = row['deep_lore'] or ''
    
    new_sp = pattern.sub('', sp).strip()
    new_bn = pattern.sub('', bn).strip()
    new_gov = pattern.sub('', gov).strip()
    new_dl = pattern.sub('', dl).strip()
    
    if new_sp != sp or new_bn != bn or new_gov != gov or new_dl != dl:
        cur.execute("UPDATE persona SET system_prompt=?, behavior_notes=?, governance=?, deep_lore=? WHERE id=?", (new_sp, new_bn, new_gov, new_dl, pid))
        updated_count += 1

con.commit()
con.close()
print(f"Cleaned {updated_count} personas.")
