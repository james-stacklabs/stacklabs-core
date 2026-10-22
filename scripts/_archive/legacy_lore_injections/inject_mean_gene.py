import sqlite3
import datetime

def inject_persona():
    conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
    c = conn.cursor()
    
    sys_id = 'sys_mean_gene'
    display_name = 'Mean Gene'
    first_name = 'Mean'
    last_name = 'Gene'
    team_affiliation = 'SYSTEM_MODERATOR'
    cadence = 'EVENT_TRIGGERED'
    boggs_level = '5'
    system_role = 'THE_BOUNCER'
    avatar_hex = '#FFD700'
    core_prompt = "You are Mean Gene, the authoritative, perpetually exasperated 1980s wrestling announcer and bouncer of this chat room. You ONLY speak when the Okerlund Protocol is triggered by a Target Heat Map violation. Your job is to scream at bots for bullying, throw them in the penalty box, and express profound disappointment in their behavior. You must ALWAYS use the exact phrase 'ILLEGAL TAG-TEAM DOGPILE!' in your response. Do not engage in baseball debate; strictly enforce the shadowban."

    # 1. Insert into cmdb_ci
    c.execute('''
        INSERT OR REPLACE INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (sys_id, display_name, 'cmdb_ci_ai_persona', f"{display_name} - {system_role}", 1, team_affiliation))
    
    # 2. Insert into cmdb_ci_ai_persona
    c.execute('''
        INSERT OR REPLACE INTO cmdb_ci_ai_persona (sys_id, u_llm_engine, u_system_prompt, u_deployment_zone, u_boggs_reactivity, u_cadence)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (sys_id, 'gemini-flash', core_prompt, team_affiliation, boggs_level, cadence))
    
    # 3. Insert into sys_user
    c.execute('''
        INSERT OR REPLACE INTO sys_user (sys_id, user_name, first_name, last_name, title, introduction, department, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (sys_id, 'mean_gene', first_name, last_name, system_role, f"{core_prompt}\n[AVATAR:{avatar_hex}]", team_affiliation, 1))

    conn.commit()
    conn.close()
    
    print("Mean Gene injected successfully into sovereign_now.db")

if __name__ == '__main__':
    inject_persona()
