import sqlite3
import re

with open('/home/james/stacklabs/01_Sovereign_Portal/public/personas_export.md') as f:
    text = f.read()

# Using a robust regex to find each profile block
profiles = {}

for block in re.split(r'(?i)##\s*#?\s*Sovereign OS Persona Profile:', text):
    if not block.strip(): continue
    lines = block.split('\n')
    name = lines[0].replace('`', '').strip().lower()
    
    content = '\n'.join(lines[1:])
    
    beh_match = re.search(r'(?i)##\s*\*?\*?BEHAVIOR EXPECTATIONS.*?((?:\n.*?)*?)(?=##\s*\*?\*?(GOVERNANCE|DEEP LORE|SYSTEM PROMPT)|$)', content)
    gov_match = re.search(r'(?i)##\s*\*?\*?GOVERNANCE.*?((?:\n.*?)*?)(?=##\s*\*?\*?(BEHAVIOR|DEEP LORE|SYSTEM PROMPT)|$)', content)
    lor_match = re.search(r'(?i)##\s*\*?\*?DEEP LORE.*?((?:\n.*?)*?)(?=##\s*\*?\*?(BEHAVIOR|GOVERNANCE|SYSTEM PROMPT)|$)', content)
    sys_match = re.search(r'(?i)##\s*\*?\*?SYSTEM PROMPT.*?((?:\n.*?)*?)(?=##\s*\*?\*?(BEHAVIOR|GOVERNANCE|DEEP LORE)|$)', content)

    sys_text = sys_match.group(1).strip() if sys_match else content.strip()
    if not sys_match:
        if beh_match: sys_text = sys_text.replace(beh_match.group(0), "")
        if gov_match: sys_text = sys_text.replace(gov_match.group(0), "")
        if lor_match: sys_text = sys_text.replace(lor_match.group(0), "")

    beh_text = beh_match.group(1).strip() if beh_match else ""
    gov_text = gov_match.group(1).strip() if gov_match else ""
    lor_text = lor_match.group(1).strip() if lor_match else ""

    profiles[name] = (sys_text.strip(), beh_text, gov_text, lor_text)

# Also load from updated_personas_apr9.json as a fallback
import json
with open('/home/james/stacklabs/dna/agents/SOVEREIGN_FANSTACK_ORACLE/payloads/updated_personas_apr9.json') as f:
    apr9 = json.load(f)
    for p in apr9:
        name = p.get('name','').lower()
        if name not in profiles:
            content = p.get('u_system_prompt', '')
            beh_match = re.search(r'(?i)##\s*\*?\*?BEHAVIOR EXPECTATIONS.*?((?:\n.*?)*?)(?=##|$)', content)
            gov_match = re.search(r'(?i)##\s*\*?\*?GOVERNANCE.*?((?:\n.*?)*?)(?=##|$)', content)
            lor_match = re.search(r'(?i)##\s*\*?\*?DEEP LORE.*?((?:\n.*?)*?)(?=##|$)', content)
            sys_match = re.search(r'(?i)##\s*\*?\*?SYSTEM PROMPT.*?((?:\n.*?)*?)(?=##|$)', content)
            sys_text = sys_match.group(1).strip() if sys_match else content
            if not sys_match:
                if beh_match: sys_text = sys_text.replace(beh_match.group(0), "")
                if gov_match: sys_text = sys_text.replace(gov_match.group(0), "")
                if lor_match: sys_text = sys_text.replace(lor_match.group(0), "")
            beh_text = beh_match.group(1).strip() if beh_match else ""
            gov_text = gov_match.group(1).strip() if gov_match else ""
            lor_text = lor_match.group(1).strip() if lor_match else ""
            profiles[name] = (sys_text.strip(), beh_text, gov_text, lor_text)


conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
c = conn.cursor()

c.execute('SELECT p.user_name FROM game_persona gp JOIN persona p ON gp.persona_id = p.id WHERE gp.game_pk="825088"')
room_users = [r[0] for r in c.fetchall()]

for user in room_users:
    ul = user.lower()
    
    # special case for coach shrubbs
    if ul == "coach shrubbs":
        continue # Already set correctly
        
    for k in profiles:
        if ul in k or k in ul:
            s, b, g, l = profiles[k]
            
            # if we found good data, update
            if b or g or l:
                print(f"Updating {user} from md... (has_beh={bool(b)}, has_gov={bool(g)}, has_lor={bool(l)})")
                c.execute("UPDATE persona SET system_prompt=?, behavior_notes=?, governance=?, deep_lore=? WHERE user_name=?", (s, b, g, l, user))
            break

conn.commit()
conn.close()
