import os
import json
import sqlite3
import uuid

PERSONAS_JSON_PATH = "/home/james/stacklabs/01_Sovereign_Portal/public/personas.json"
LORE_DIR = "/home/james/stacklabs/dna/agents/personas"
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def migrate_personas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    with open(PERSONAS_JSON_PATH, "r") as f:
        personas = json.load(f)

    # Clear previous so we can rerun safely
    c.execute("DELETE FROM sys_user")
    c.execute("DELETE FROM sys_user_group")
    c.execute("DELETE FROM sys_user_grmember")
    
    group_cache = {}

    for persona in personas:
        call_sign = persona.get("name", "Unknown")
        prompt = persona.get("u_system_prompt", "")
        zone = persona.get("u_deployment_zone", "global")
        team = persona.get("team", "Unknown")
        
        # 1. Manage Groups
        if team not in group_cache:
            group_id = uuid.uuid4().hex
            c.execute("INSERT INTO sys_user_group (sys_id, name, description) VALUES (?, ?, ?)", 
                      (group_id, team, f"AI Persona Deployment Group for {team}"))
            group_cache[team] = group_id
        else:
            group_id = group_cache[team]

        # 2. Get Lore from markdown
        lore_content = prompt
        try:
            normalized_name = call_sign.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
            lore_path = os.path.join(LORE_DIR, f"{normalized_name}.md")
            if os.path.exists(lore_path):
                with open(lore_path, "r") as lf:
                    lore_content = lf.read()
            else:
                print(f"No markdown found for {call_sign}")
        except Exception as e:
            print(e)
            pass
            
        # 3. Create sys_user
        if 'id' in persona:
            sys_id = persona['id'] # keep old IDs if possible
        else:
            sys_id = uuid.uuid4().hex
            
        c.execute("""
            INSERT INTO sys_user (sys_id, user_name, first_name, last_name, title, introduction, city, department, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (sys_id, normalized_name, call_sign, "(Sovereign Entity)", 
              prompt[:150] + "..." if len(prompt)>150 else prompt, 
              lore_content, zone, persona.get("u_llm_engine", "gemini")))
              
        # 4. Map user to group
        member_id = uuid.uuid4().hex
        c.execute("INSERT INTO sys_user_grmember (sys_id, user, group_id) VALUES (?, ?, ?)", (member_id, sys_id, group_id))
        
        print(f"Migrated {call_sign} -> Group {team}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate_personas()
