import sqlite3
import re

db_path = '/home/james/stacklabs/dna/sovereign_now.db'

TEAM_MAP = {
    'san diego padres': 'SD',
    'pittsburgh pirates': 'PIT',
    'kansas city royals': 'KC',
    'detroit': 'DET',
    'min': 'MIN',
    'az': 'ARI',
    'ath': 'OAK', # Athletics? Or ATH? Wait, OAK
    'laa': 'LAA',
    'nym': 'NYM',
    'phi': 'PHI',
    'sf': 'SF',
    'cle': 'CLE',
    'kc': 'KC',
    'atl': 'ATL',
    'bos': 'BOS',
    'bal': 'BAL',
    'cws': 'CWS',
    'sea': 'SEA',
    'tex': 'TEX',
    'hou': 'HOU',
    'col': 'COL',
    'wsh': 'WSH',
    'chc': 'CHC',
    'tb': 'TB',
    'cin': 'CIN',
    'mia': 'MIA',
    'nyy': 'NYY',
    'lad': 'LAD',
    'tor': 'TOR',
    'sd': 'SD',
    'pit': 'PIT'
}

def clean_assigned_to(val):
    if not val:
        return val
    v = val.lower().strip()
    if v in TEAM_MAP:
        return TEAM_MAP[v]
    # Check if it's already uppercase abbreviation
    if val.upper() in TEAM_MAP.values():
        return val.upper()
    return val # Return as is if unknown

def parse_lore(prompt):
    if not prompt:
        return prompt, "", "", ""
    
    role = ""
    behavior = ""
    governance = ""
    deep_lore = ""
    
    # Split by markdown headers
    parts = re.split(r'\n##\s+', '\n' + prompt)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        lower_p = p.lower()
        if lower_p.startswith('role') or lower_p.startswith('**role'):
            role = p
        elif lower_p.startswith('behavior') or lower_p.startswith('**behavior'):
            behavior = p
        elif lower_p.startswith('governance') or lower_p.startswith('**governance'):
            governance = p
        else:
            if deep_lore:
                deep_lore += "\n\n## " + p
            else:
                deep_lore = "## " + p
    
    if not role and not behavior and not deep_lore:
        role = prompt
    
    if role.startswith('ROLE') or role.startswith('**ROLE'):
        role = re.sub(r'^\*?\*?ROLE\*?\*?\s*[:\n]*\s*', '', role, flags=re.IGNORECASE)
    
    return role.strip(), behavior.strip(), governance.strip(), deep_lore.strip()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT * FROM cmdb_ci_ai_persona")
personas = c.fetchall()

seen_prompts = set()
duplicates = []
updates = []

for p in personas:
    sys_id = p['sys_id']
    prompt = p['u_system_prompt']
    
    if prompt and prompt in seen_prompts:
        duplicates.append(sys_id)
        continue
    
    if prompt:
        seen_prompts.add(prompt)
    
    c.execute("SELECT assigned_to FROM cmdb_ci WHERE sys_id=?", (sys_id,))
    ci_row = c.fetchone()
    assigned_to = ci_row['assigned_to'] if ci_row else None
    
    new_assigned = clean_assigned_to(assigned_to)
    
    role, behavior, gov, lore = parse_lore(prompt)
    
    updates.append({
        'sys_id': sys_id,
        'role': role,
        'behavior': behavior,
        'gov': gov,
        'lore': lore,
        'assigned': new_assigned
    })

print(f"Found {len(duplicates)} duplicates to delete.")

for sys_id in duplicates:
    c.execute("DELETE FROM cmdb_ci_ai_persona WHERE sys_id=?", (sys_id,))
    c.execute("DELETE FROM cmdb_ci WHERE sys_id=?", (sys_id,))
    c.execute("DELETE FROM sys_user WHERE sys_id=?", (sys_id,))

for u in updates:
    c.execute("""
        UPDATE cmdb_ci_ai_persona 
        SET u_system_prompt=?, u_behavior_expectations=?, u_governance_boundaries=?, u_deep_lore=?
        WHERE sys_id=?
    """, (u['role'], u['behavior'], u['gov'], u['lore'], u['sys_id']))
    
    if u['assigned']:
        c.execute("UPDATE cmdb_ci SET assigned_to=? WHERE sys_id=?", (u['assigned'], u['sys_id']))
        
    intro = u['role']
    if intro is None:
        intro = ""
    elif len(intro) > 300:
        intro = intro[:297] + '...'
    c.execute("UPDATE sys_user SET active=1, introduction=? WHERE sys_id=?", (intro, u['sys_id']))

conn.commit()
conn.close()
print("Cleanup complete!")
