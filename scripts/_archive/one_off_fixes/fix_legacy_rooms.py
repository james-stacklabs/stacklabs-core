import sqlite3
import re

def score_persona(persona, keywords):
    score = 0
    text = (persona['title'] + ' ' + persona['introduction']).lower()
    for kw in keywords:
        score += len(re.findall(r'\b' + kw.lower() + r'\b', text))
    return score

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get valid personas
cursor.execute("SELECT sys_id, user_name, title, introduction FROM sys_user")
data = [dict(row) for row in cursor.fetchall()]
candidates = []
for p in data:
    p['title'] = p['title'] or ''
    p['introduction'] = p['introduction'] or ''
    if not re.search(r'_\d+$', p['user_name']) and p['user_name'] not in ['wardy', 'dot']:
        candidates.append(p)

generic = ['city', 'team', 'club', 'los', 'san', 'new', 'york', 'st.', 'bay', 'white', 'red', 'blue', 'the']

# Get all rooms
cursor.execute("SELECT sys_id, name, game_pk FROM cmdb_ci_fanstack_room")
rooms = cursor.fetchall()

for room in rooms:
    room_sys_id = room['sys_id']
    game_pk = room['game_pk']
    name = room['name']
    
    # Parse name: Game 822830 (Minnesota Twins@Toronto Blue Jays)
    match = re.search(r'\((.*?)@([^)]+)\)', name)
    if not match: continue
    
    away_team = match.group(1).lower().strip()
    home_team = match.group(2).lower().strip()
    
    home_keywords = [k for k in home_team.split() if k not in generic] + [home_team]
    away_keywords = [k for k in away_team.split() if k not in generic] + [away_team]
    
    if 'athletics' in home_team: home_keywords.extend(["a's", "oakland"])
    if 'athletics' in away_team: away_keywords.extend(["a's", "oakland"])
    if 'diamondbacks' in home_team: home_keywords.extend(["d-backs", "dbacks"])
    if 'diamondbacks' in away_team: away_keywords.extend(["d-backs", "dbacks"])
    
    # Score Home
    home_scored = [(p, score_persona(p, home_keywords)) for p in candidates]
    home_scored.sort(key=lambda x: x[1], reverse=True)
    home_selected = [x[0] for x in home_scored if x[1] >= 2][:3]
    
    # Score Away
    temp_candidates = [c for c in candidates if c not in home_selected]
    away_scored = [(p, score_persona(p, away_keywords)) for p in temp_candidates]
    away_scored.sort(key=lambda x: x[1], reverse=True)
    away_selected = [x[0] for x in away_scored if x[1] >= 2][:3]
    
    # Assign and replace
    cursor.execute("SELECT sys_id FROM sys_user_group WHERE name = ?", (f"room_{game_pk}",))
    group = cursor.fetchone()
    if not group: continue
    group_sys_id = group['sys_id']
    
    cursor.execute("DELETE FROM sys_user_grmember WHERE group_id = ?", (group_sys_id,))
    
    # Add back
    members = home_selected + away_selected
    for m in members:
        cursor.execute("INSERT INTO sys_user_grmember (sys_id, user, group_id) VALUES (lower(hex(randomblob(16))), ?, ?)", (m['sys_id'], group_sys_id))
    
    # Add dot and wardy
    for agent in ['dot', 'wardy']:
        cursor.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (agent,))
        agent_row = cursor.fetchone()
        if agent_row:
            cursor.execute("INSERT INTO sys_user_grmember (sys_id, user, group_id) VALUES (lower(hex(randomblob(16))), ?, ?)", (agent_row['sys_id'], group_sys_id))
            members.append({'user_name': agent})
            
    print(f"Fixed {name} with {len(members)} personas: {[m['user_name'] for m in members]}")

conn.commit()
conn.close()
