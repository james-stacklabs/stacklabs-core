import json
import sqlite3
import re
import uuid

def score_persona(persona, keywords):
    score = 0
    text = (persona.get('title', '') + ' ' + persona.get('introduction', '')).lower()
    for kw in keywords:
        score += len(re.findall(r'\b' + kw + r'\b', text))
    return score

def main():
    db_path = '/home/james/stacklabs/dna/sovereign_now.db'
    json_path = '/home/james/stacklabs/dna/dropzone/json/fanstack_personas.json'

    with open(json_path) as f:
        data = json.load(f)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Alter room table to add boggs_level and room_state
    try:
        cursor.execute("ALTER TABLE cmdb_ci_fanstack_room ADD COLUMN boggs_level INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE cmdb_ci_fanstack_room ADD COLUMN room_state TEXT DEFAULT 'inactive'")
    except sqlite3.OperationalError:
        pass

    # Mass import to sys_user
    for p in data:
        # Check if exists
        cursor.execute("SELECT sys_id FROM sys_user WHERE sys_id = ?", (p['sys_id'],))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO sys_user (sys_id, user_name, first_name, last_name, title, introduction, city, department, active) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (p.get('sys_id'), p.get('user_name'), p.get('first_name'), p.get('last_name'), 
                  p.get('title'), p.get('introduction'), p.get('city'), p.get('department'), p.get('active', 1)))
        else:
            cursor.execute("""
                UPDATE sys_user SET user_name=?, first_name=?, last_name=?, title=?, introduction=?, city=?, department=?, active=?
                WHERE sys_id=?
            """, (p.get('user_name'), p.get('first_name'), p.get('last_name'), p.get('title'), 
                  p.get('introduction'), p.get('city'), p.get('department'), p.get('active', 1), p.get('sys_id')))

    conn.commit()

    # Find the DOT and WARDY personas
    dot = next((p for p in data if p['user_name'] == 'dot'), None)
    wordy = next((p for p in data if p['user_name'] == 'wordy'), None)

    teams = {
        'AZ': ['diamondbacks', 'd-backs', 'arizona'],
        'PHI': ['phillies', 'philly', 'phanatic'],
        'MIA': ['marlins', 'miami'],
        'DET': ['tigers', 'detroit'],
        'BAL': ['orioles', 'baltimore', 'os'],
        'CLE': ['guardians', 'cleveland', 'clevy']
    }

    selected = {k: [] for k in teams}

    # Don't pick dot or wordy for the team slots
    candidates = [p for p in data if p['user_name'] not in ['dot', 'wordy']]

    for t_name, keywords in teams.items():
        scored = [(p, score_persona(p, keywords)) for p in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        # pick top 3
        # Ensure they actually matched something
        valid = [x[0] for x in scored if x[1] > 0]
        selected[t_name] = valid[:3]
        # remove selected so they aren't double counted if there's overlap
        for s in selected[t_name]:
            candidates.remove(s)

    games = [
        {'pk': '823480', 'away': 'AZ', 'home': 'PHI', 'boggs': 3},  # rivalry maybe higher boggs
        {'pk': '824294', 'away': 'MIA', 'home': 'DET', 'boggs': 1},
        {'pk': '824453', 'away': 'BAL', 'home': 'CLE', 'boggs': 2}
    ]

    for game in games:
        room_name = f"Game {game['pk']} ({game['away']}@{game['home']})"
        room_key = f"room_{game['pk']}"
        group_id = room_key # Using room_key as sys_id for the group for simplicity, or generate a uuid

        # Check if room exists
        cursor.execute("SELECT sys_id FROM cmdb_ci_fanstack_room WHERE game_pk = ?", (game['pk'],))
        room = cursor.fetchone()
        if not room:
            room_sys_id = str(uuid.uuid4()).replace('-', '')
            cursor.execute("""
                INSERT INTO cmdb_ci_fanstack_room (sys_id, name, room_key, game_pk, is_simulated, sim_speed, u_cadence, boggs_level, room_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (room_sys_id, room_name, room_key, game['pk'], 1, 1.0, 'pacer', game['boggs'], 'active'))
        else:
            room_sys_id = room[0]
            cursor.execute("UPDATE cmdb_ci_fanstack_room SET boggs_level=?, room_state='active' WHERE sys_id=?", (game['boggs'], room_sys_id))

        # Check if user group exists
        cursor.execute("SELECT sys_id FROM sys_user_group WHERE name = ?", (room_name,))
        group = cursor.fetchone()
        if not group:
            group_sys_id = str(uuid.uuid4()).replace('-', '')
            cursor.execute("INSERT INTO sys_user_group (sys_id, name, description, active) VALUES (?, ?, ?, ?)", 
                           (group_sys_id, room_name, f"Group for {room_name}", 1))
        else:
            group_sys_id = group[0]

        # Clear existing members
        cursor.execute("DELETE FROM sys_user_grmember WHERE group_id = ?", (group_sys_id,))

        # Add new members
        members_to_add = selected[game['away']] + selected[game['home']]
        if dot: members_to_add.append(dot)
        if wordy: members_to_add.append(wordy)

        for p in members_to_add:
            mem_id = str(uuid.uuid4()).replace('-', '')
            cursor.execute("INSERT INTO sys_user_grmember (sys_id, user, group_id) VALUES (?, ?, ?)",
                           (mem_id, p['sys_id'], group_sys_id))
            
        print(f"Room {room_name} configured with {len(members_to_add)} personas.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
