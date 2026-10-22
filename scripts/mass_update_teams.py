import sqlite3
import re
import json
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.api_client import resolve_team_name

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
PARSED_TEAMS_PATH = '/home/james/stacklabs/scratch/parsed_teams.json'

def determine_team(text):
    if not text:
        return 'global'
    # Try resolving whole text first
    res = resolve_team_name(text)
    if res and res != "GLOBAL":
        return res
    # Token check across words
    for word in re.findall(r'\b\w+\b', text.lower()):
        res = resolve_team_name(word)
        if res and res != "GLOBAL":
            return res
    return 'global'

def mass_update():
    # Load parsed teams blueprint
    parsed_teams = {}
    if os.path.exists(PARSED_TEAMS_PATH):
        try:
            with open(PARSED_TEAMS_PATH, 'r') as f:
                parsed_teams = {k.lower(): v for k, v in json.load(f).items()}
        except Exception as e:
            print(f"Warning: Failed to load parsed_teams.json: {e}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Load canonical teams from persona table
    persona_teams = {}
    try:
        cur.execute("SELECT user_name, team FROM persona")
        persona_teams = {row[0].lower(): row[1] for row in cur.fetchall() if row[1]}
    except Exception as e:
        print(f"Warning: Failed to load persona table teams: {e}")
    
    cur.execute("""
        SELECT u.sys_id, u.user_name, u.introduction, p.u_system_prompt, p.u_deep_lore, p.u_behavior_expectations
        FROM sys_user u
        JOIN cmdb_ci_ai_persona p ON u.sys_id = p.sys_id
    """)
    rows = cur.fetchall()
    
    updates = 0
    for sys_id, user_name, intro, prompt, lore, behavior in rows:
        uname_lower = user_name.lower()
        
        # Prioritize parsed_teams.json blueprint, then persona database column, then keyword match
        if uname_lower in parsed_teams:
            assigned_to = parsed_teams[uname_lower]
        elif uname_lower in persona_teams:
            assigned_to = persona_teams[uname_lower]
        else:
            combined_text = f"{user_name} {intro or ''} {prompt or ''} {lore or ''} {behavior or ''}"
            assigned_to = determine_team(combined_text)
        
        # Exceptions
        if user_name in ['mr_wonderful', 'cuban', 'lori', 'barbara', 'wardy', 'dot', 'scruffy', 'eileen', 'james']:
            assigned_to = 'global'
            
        # Update cmdb_ci (assigned_to)
        cur.execute("UPDATE cmdb_ci SET assigned_to = ? WHERE sys_id = ?", (assigned_to, sys_id))
        
        # Update sys_user (active = 1, department = assigned_to to keep in sync)
        cur.execute("UPDATE sys_user SET active = 1, department = ? WHERE sys_id = ?", (assigned_to, sys_id))
        
        # Update cmdb_ci_ai_persona (u_deployment_zone = '')
        cur.execute("UPDATE cmdb_ci_ai_persona SET u_deployment_zone = '' WHERE sys_id = ?", (sys_id,))
        
        updates += 1
        
    conn.commit()
    conn.close()
    print(f"Mass update complete. Updated {updates} records.")

if __name__ == "__main__":
    mass_update()
