import sqlite3
import random

TEAM_ACRONYMS = {
    'kc': 'kansas city royals',
    'bal': 'baltimore orioles',
    'nym': 'new york mets',
    'nyy': 'new york yankees',
    'hou': 'houston astros',
    'stl': 'st. louis cardinals',
    'det': 'detroit tigers',
    'col': 'colorado rockies',
    'min': 'minnesota twins',
    'cin': 'cincinnati reds',
    'lad': 'los angeles dodgers',
    'sd': 'san diego padres',
    'laa': 'los angeles angels',
    'tex': 'texas rangers',
    'sea': 'seattle mariners',
    'tor': 'toronto blue jays',
    'ari': 'arizona diamondbacks',
    'cws': 'chicago white sox',
    'oak': 'athletics',
    'chc': 'chicago cubs',
    'sf': 'san francisco giants',
    'wsh': 'washington nationals',
    'tb': 'tampa bay rays',
    'pit': 'pittsburgh pirates',
    'bos': 'boston red sox',
    'mil': 'milwaukee brewers',
    'mia': 'miami marlins',
    'cle': 'cleveland guardians',
    'atl': 'atlanta braves',
    'phi': 'philadelphia phillies'
}

def fix_m2m():
    conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
    c = conn.cursor()
    c.execute("SELECT game_pk, name FROM cmdb_ci_fanstack_room")
    games = c.fetchall()
    c.execute("SELECT name, MAX(assigned_to) FROM cmdb_ci WHERE sys_class_name = 'cmdb_ci_ai_persona' GROUP BY name")
    personas = c.fetchall()
    
    team_map = {}
    for p in personas:
        if p[0].lower() in ['dot', 'wordy', 'wardy']: continue
        raw_t = p[1].lower().strip() if p[1] else ''
        t = TEAM_ACRONYMS.get(raw_t, raw_t)
        if t not in team_map: team_map[t] = []
        team_map[t].append(p[0])
        
    c.execute("DELETE FROM m2m_persona_room")
    
    for g in games:
        pk = g[0]
        matchup = g[1].lower().replace("st. louis", "st. louis").replace("athletics", "athletics")
        
        pool = []
        for t, fans in team_map.items():
            if t and t in matchup:
                pool.extend(fans)
                
        random.shuffle(pool)
        selected = pool[:6]
        
        if len(selected) < 6:
            all_fans = [p[0] for p in personas if p[0].lower() not in ['dot', 'wordy', 'wardy'] and p[0] not in selected]
            random.shuffle(all_fans)
            selected.extend(all_fans[:6-len(selected)])
            
        selected.append('dot')
        selected.append('wordy')
        if 'mets' in matchup or 'nym' in matchup:
            if 'barf' not in selected:
                selected.append('barf')
        
        for p_name in selected:
            c.execute("INSERT INTO m2m_persona_room (persona, room) VALUES (?, ?)", (p_name, pk))
            
    conn.commit()
    print("M2M explicitly mapped.")

if __name__ == "__main__":
    fix_m2m()
