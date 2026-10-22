import sqlite3
import re
import os
import glob
from datetime import datetime

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
harvested_dir = '/home/james/stacklabs/media_vault/03_Assets/Harvested_Artifacts/'

personas = {}

# 1. Parse the short bios
with open(os.path.join(harvested_dir, 'cd909a28_sovereign_persona_export.md'), 'r') as f:
    lines = f.readlines()
    
    current_persona = None
    for line in lines:
        line = line.strip()
        m = re.match(r'^###\s+([a-zA-Z0-9_-]+)(?:\s|$)', line)
        if m:
            current_persona = m.group(1).lower()
            if current_persona not in personas:
                personas[current_persona] = {'deep_lore': ''}
        elif current_persona and line.startswith('>'):
            personas[current_persona]['deep_lore'] += line[1:].strip() + " "

# Clean up spaces
for p in personas:
    personas[p]['deep_lore'] = personas[p]['deep_lore'].strip()

# 2. Parse the detailed bios
detailed_files = glob.glob(os.path.join(harvested_dir, '*_review.md')) + glob.glob(os.path.join(harvested_dir, '*_personas.md'))

for file_path in detailed_files:
    if 'cd909a28' in file_path: continue
    with open(file_path, 'r') as f:
        content = f.read()
    
    profiles = re.split(r'(?i)#\s+SOVEREIGN OS PERSONA PROFILE:\s*', content)
    for profile in profiles[1:]:
        lines = profile.split('\n')
        name_line = lines[0].strip()
        name_match = re.match(r'([a-zA-Z0-9_]+)', name_line)
        if not name_match: continue
        name = name_match.group(1).lower()
        
        if name not in personas:
            personas[name] = {}
            
        current_section = None
        for line in lines[1:]:
            line_stripped = line.strip()
            if re.match(r'^##\s+ROLE', line_stripped, re.I):
                current_section = 'system_prompt'
                personas[name][current_section] = []
            elif re.match(r'^##\s+BEHAVIOR EXPECTATIONS', line_stripped, re.I):
                current_section = 'behavior_notes'
                personas[name][current_section] = []
            elif re.match(r'^##\s+GOVERNANCE & BOUNDARIES', line_stripped, re.I):
                current_section = 'governance'
                personas[name][current_section] = []
            elif re.match(r'^##\s+DEEP LORE', line_stripped, re.I):
                current_section = 'deep_lore'
                personas[name][current_section] = []
            elif re.match(r'^##\s+', line_stripped):
                current_section = None
            elif current_section:
                personas[name][current_section].append(line)
        
        for k in ['system_prompt', 'behavior_notes', 'governance', 'deep_lore']:
            if k in personas[name] and isinstance(personas[name][k], list):
                personas[name][k] = "\n".join(personas[name][k]).strip()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

updated_count = 0
now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

for name, data in personas.items():
    update_cols = []
    update_vals = []
    
    if 'system_prompt' in data and data['system_prompt']:
        update_cols.append("system_prompt = ?")
        update_vals.append(data['system_prompt'])
    if 'behavior_notes' in data and data['behavior_notes']:
        update_cols.append("behavior_notes = ?")
        update_vals.append(data['behavior_notes'])
    if 'governance' in data and data['governance']:
        update_cols.append("governance = ?")
        update_vals.append(data['governance'])
    if 'deep_lore' in data and data['deep_lore']:
        update_cols.append("deep_lore = ?")
        update_vals.append(data['deep_lore'])
        
    if update_cols:
        update_cols.append("updated_at = ?")
        update_vals.append(now_str)
        
        query = f"UPDATE persona SET {', '.join(update_cols)} WHERE LOWER(user_name) = ?"
        update_vals.append(name)
        cursor.execute(query, update_vals)
        if cursor.rowcount > 0:
            updated_count += 1
            print(f"Updated {name}")

conn.commit()
conn.close()
print(f"\nTotal personas updated: {updated_count}")
