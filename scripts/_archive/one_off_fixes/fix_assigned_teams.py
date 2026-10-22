import sqlite3
import re

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

TEAM_MAP = {
    'yankees': 'NYY', 'bronx': 'NYY', 'pinstripe': 'NYY', 'judge': 'NYY', 'cole': 'NYY',
    'mets': 'NYM', 'queens': 'NYM', 'citifield': 'NYM', 'amazins': 'NYM',
    'red sox': 'BOS', 'fenway': 'BOS', 'boston': 'BOS', 'green monster': 'BOS',
    'dodgers': 'LAD', 'chavez ravine': 'LAD', 'los angeles dodgers': 'LAD', 'ohtani': 'LAD',
    'giants': 'SF', 'oracle': 'SF', 'san francisco': 'SF', 'mccovey': 'SF',
    'padres': 'SD', 'gaslamp': 'SD', 'friar': 'SD', 'san diego': 'SD',
    'cubs': 'CHC', 'wrigley': 'CHC', 'chicago cubs': 'CHC', 'north side': 'CHC', 'ivy': 'CHC',
    'white sox': 'CWS', 'south side': 'CWS', 'chicago white sox': 'CWS',
    'braves': 'ATL', 'atlanta': 'ATL', 'truist': 'ATL', 'tomahawk': 'ATL',
    'phillies': 'PHI', 'philadelphia': 'PHI', 'citizens bank': 'PHI', 'phanatic': 'PHI', 'battery': 'PHI',
    'astros': 'HOU', 'houston': 'HOU', 'minute maid': 'HOU', 'space city': 'HOU',
    'rangers': 'TEX', 'texas': 'TEX', 'arlington': 'TEX', 'globe life': 'TEX',
    'mariners': 'SEA', 'seattle': 'SEA', 't-mobile': 'SEA',
    'angels': 'LAA', 'anaheim': 'LAA', 'halo': 'LAA', 'rally monkey': 'LAA',
    'athletics': 'OAK', 'oakland': 'OAK', 'coliseum': 'OAK', 'possum': 'OAK', 'sacramento': 'OAK', 'vegas': 'OAK',
    'diamondbacks': 'ARI', 'arizona': 'ARI', 'd-backs': 'ARI', 'snakes': 'ARI',
    'rockies': 'COL', 'colorado': 'COL', 'coors': 'COL',
    'marlins': 'MIA', 'miami': 'MIA', 'cafecito': 'MIA',
    'rays': 'TB', 'tampa bay': 'TB', 'tropicana': 'TB', 'trop': 'TB', 'flappy': 'TB',
    'blue jays': 'TOR', 'toronto': 'TOR', 'rogers centre': 'TOR', 'maple': 'TOR', 'poutine': 'TOR',
    'orioles': 'BAL', 'baltimore': 'BAL', 'camden': 'BAL', 'birdland': 'BAL',
    'guardians': 'CLE', 'cleveland': 'CLE', 'progressive': 'CLE', 'muni': 'CLE',
    'tigers': 'DET', 'detroit': 'DET', 'comerica': 'DET', 'paws': 'DET',
    'twins': 'MIN', 'minnesota': 'MIN', 'target field': 'MIN', 'jucy lucy': 'MIN',
    'royals': 'KC', 'kansas city': 'KC', 'kauffman': 'KC',
    'reds': 'CIN', 'cincinnati': 'CIN', 'great american': 'CIN', 'skyline': 'CIN',
    'brewers': 'MIL', 'milwaukee': 'MIL', 'amfam': 'MIL', 'bernie': 'MIL', 'cream city': 'MIL',
    'cardinals': 'STL', 'st. louis': 'STL', 'busch': 'STL', 'redbird': 'STL',
    'pirates': 'PIT', 'pittsburgh': 'PIT', 'pnc': 'PIT', 'jolly roger': 'PIT', 'steel city': 'PIT',
    'nationals': 'WSH', 'washington': 'WSH', 'nats': 'WSH'
}

def determine_team(user_name, combined_text):
    text = combined_text.lower()
    uname = user_name.lower()
    
    # First check user_name for explicit team tags
    uname_normalized = uname.replace('_', ' ')
    for keyword, team_code in TEAM_MAP.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', uname_normalized) or keyword == uname_normalized:
            return team_code

    # Count occurrences of all keywords in the text
    scores = {}
    for keyword, team_code in TEAM_MAP.items():
        count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
        if count > 0:
            scores[team_code] = scores.get(team_code, 0) + count
            
    if scores:
        return max(scores, key=scores.get)
    return 'global'

def fix_teams():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT u.sys_id, u.user_name, u.introduction, p.u_system_prompt, p.u_deep_lore, p.u_behavior_expectations
        FROM sys_user u
        JOIN cmdb_ci_ai_persona p ON u.sys_id = p.sys_id
    """)
    rows = cur.fetchall()
    
    updates = 0
    for sys_id, user_name, intro, prompt, lore, behavior in rows:
        combined_text = f"{intro or ''} {prompt or ''} {lore or ''} {behavior or ''}"
        assigned_to = determine_team(user_name, combined_text)
        
        # Exceptions
        if user_name in ['mr_wonderful', 'cuban', 'lori', 'barbara', 'wardy', 'dot', 'scruffy', 'eileen', 'james']:
            assigned_to = 'global'
            
        cur.execute("UPDATE cmdb_ci SET assigned_to = ? WHERE sys_id = ?", (assigned_to, sys_id))
        updates += 1
        
    conn.commit()
    conn.close()
    print(f"Fixed teams. Updated {updates} records.")

if __name__ == "__main__":
    fix_teams()
