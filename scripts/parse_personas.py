import sqlite3
import re

def split_bio(text):
    if not text:
        return "", "", "", ""
        
    system_prompt = text
    behavior = ""
    governance = ""
    deep_lore = ""
    
    # Try to find headers
    # Behavior Expectations
    b_match = re.search(r'(?i)(##\s*\*?\*?BEHAVIOR EXPECTATIONS.*?(?=##|$))', text, re.DOTALL)
    if b_match:
        behavior = b_match.group(1).strip()
        text = text.replace(b_match.group(1), "")
        
    g_match = re.search(r'(?i)(##\s*\*?\*?GOVERNANCE.*?BOUNDARIES.*?(?=##|$))', text, re.DOTALL)
    if g_match:
        governance = g_match.group(1).strip()
        text = text.replace(g_match.group(1), "")
        
    d_match = re.search(r'(?i)(##\s*\*?\*?DEEP LORE.*?(?=##|$))', text, re.DOTALL)
    if d_match:
        deep_lore = d_match.group(1).strip()
        text = text.replace(d_match.group(1), "")
        
    system_prompt = text.strip()
    return system_prompt, behavior, governance, deep_lore

conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
c = conn.cursor()

c.execute("SELECT user_name, system_prompt FROM persona")
rows = c.fetchall()

for row in rows:
    user, prompt = row
    sp, b, g, d = split_bio(prompt)
    if b or g or d:
        c.execute("UPDATE persona SET system_prompt=?, behavior_notes=?, governance=?, deep_lore=? WHERE user_name=?", (sp, b, g, d, user))

conn.commit()
conn.close()
print("Personas parsed and updated.")
