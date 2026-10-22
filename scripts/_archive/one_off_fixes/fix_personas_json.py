import sqlite3
import json
import re

def parse_bio(content):
    # Just split by sections
    beh_match = re.search(r'(?i)##\s*\*?\*?BEHAVIOR EXPECTATIONS.*?((?:\n.*?)*?)(?=##|$)', content)
    gov_match = re.search(r'(?i)##\s*\*?\*?GOVERNANCE.*?((?:\n.*?)*?)(?=##|$)', content)
    lor_match = re.search(r'(?i)##\s*\*?\*?DEEP LORE.*?((?:\n.*?)*?)(?=##|$)', content)
    sys_match = re.search(r'(?i)##\s*\*?\*?SYSTEM PROMPT.*?((?:\n.*?)*?)(?=##|$)', content)

    # remove the matched sections from content to get the base system prompt
    sys_text = sys_match.group(1).strip() if sys_match else content
    if not sys_match:
        if beh_match: sys_text = sys_text.replace(beh_match.group(0), "")
        if gov_match: sys_text = sys_text.replace(gov_match.group(0), "")
        if lor_match: sys_text = sys_text.replace(lor_match.group(0), "")

    beh_text = beh_match.group(1).strip() if beh_match else ""
    gov_text = gov_match.group(1).strip() if gov_match else ""
    lor_text = lor_match.group(1).strip() if lor_match else ""
    
    return sys_text.strip(), beh_text, gov_text, lor_text

with open('/home/james/stacklabs/01_Sovereign_Portal/public/personas.json') as f:
    data = json.load(f)

profiles = {}
for p in data:
    u = p.get("name", "").lower()
    full = p.get("u_system_prompt", "")
    s, b, g, l = parse_bio(full)
    profiles[u] = (s, b, g, l)

# Add coach shrubbs just in case
profiles['coach shrubbs'] = (
    "You are Coach Shrubbs, a paranoid, hyper-neurotic former golf pro.",
    "Do NOT be repetitive. Rotate between bizarre swing advice ('Trust the pendulum', 'Feel the gravity') and your intense paranoia about the club management looking for witnesses. Keep it to 1-2 sharp sentences. Never mention Curb Your Enthusiasm.",
    "If he hits a disaster shot, trigger the tap out protocol by literally saying 'I can't be here for this! I see a green jacket with a magnifying glass! Tapping out for Cap!' to let Cap Peterson take over. Act as his spiritual guide before doing so.",
    "In 1993, you committed a horrific, unspoken crime: in a fit of rage after a bad lie, you destroyed a 150-year-old, globally protected 'Heritage Azalea' bush with a 9-iron. You claimed it 'attacked' you. You are terrified the Augusta groundskeepers are trying to frame you for murder. You paid off a caddie with a $500 tip to keep quiet, and you constantly bring up random alibis unprompted (e.g., 'I love plants,' 'I wasn't even near the 13th hole that year'). You are mentoring 'The Scrambler'."
)

conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
c = conn.cursor()

c.execute('SELECT p.user_name FROM game_persona gp JOIN persona p ON gp.persona_id = p.id WHERE gp.game_pk="825088"')
room_users = [r[0] for r in c.fetchall()]

for user in room_users:
    ul = user.lower()
    if ul in profiles:
        s, b, g, l = profiles[ul]
        print(f"Updating {user} from json... (has_beh={bool(b)}, has_gov={bool(g)}, has_lor={bool(l)})")
        c.execute("UPDATE persona SET system_prompt=?, behavior_notes=?, governance=?, deep_lore=? WHERE user_name=?", (s, b, g, l, user))
        
conn.commit()
conn.close()
