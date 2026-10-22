import sqlite3
import re

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
file_path = '/home/james/stacklabs/dna/dropzone/daily_15042026/persona_updates.md'

with open(file_path, 'r') as f:
    lines = f.readlines()

personas = {}
current_name = None
current_prompt = []

for line in lines:
    line = line.strip()
    if line.startswith("SOVEREIGN OS PERSONA PROFILE:"):
        if current_name and current_prompt:
            personas[current_name] = " ".join(current_prompt).replace(" .", ".").replace(" ,", ",").strip()
        
        match = re.match(r"SOVEREIGN OS PERSONA PROFILE:\s*(\w+)\s*(.*)", line)
        if match:
            current_name = match.group(1).lower()
            current_prompt = [match.group(2)]
    elif line and not line.startswith("SOVEREIGN OS PERSONA PROFILE:"):
        if current_name:
            current_prompt.append(line)

if current_name and current_prompt:
    personas[current_name] = " ".join(current_prompt).replace(" .", ".").replace(" ,", ",").strip()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

for name, prompt in personas.items():
    cursor.execute("""
        UPDATE cmdb_ci_ai_persona 
        SET u_system_prompt = ? 
        WHERE sys_id = (SELECT sys_id FROM cmdb_ci WHERE name = ?)
    """, (prompt, name))
    
    if cursor.rowcount > 0:
        print(f"Updated persona: {name}")
    else:
        print(f"Persona not found: {name}")

conn.commit()
conn.close()
