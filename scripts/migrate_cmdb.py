import sqlite3
import json
import uuid
import os

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def migrate():
    # Attempt to close existing connections by just doing it now
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Create cmdb_ci
    c.execute("""
    CREATE TABLE IF NOT EXISTS cmdb_ci (
        sys_id TEXT PRIMARY KEY,
        name TEXT,
        sys_class_name TEXT,
        short_description TEXT,
        operational_status INTEGER DEFAULT 1,
        assigned_to TEXT
    )
    """)

    # 2. Create cmdb_ci_ai_persona
    c.execute("""
    CREATE TABLE IF NOT EXISTS cmdb_ci_ai_persona (
        sys_id TEXT PRIMARY KEY,
        u_system_prompt TEXT,
        u_deployment_zone TEXT,
        u_boggs_reactivity TEXT,
        u_cadence TEXT
    )
    """)

    # 3. Create m2m_persona_room
    c.execute("""
    CREATE TABLE IF NOT EXISTS m2m_persona_room (
        sys_id TEXT PRIMARY KEY,
        persona TEXT,
        room TEXT,
        prompt_overlay TEXT
    )
    """)

    # 4. Create cmdb_ci_fanstack_room
    c.execute("""
    CREATE TABLE IF NOT EXISTS cmdb_ci_fanstack_room (
        sys_id TEXT PRIMARY KEY,
        name TEXT,
        room_key TEXT,
        game_pk TEXT,
        is_simulated INTEGER,
        sim_speed REAL
    )
    """)

    # Move from sys_user if needed
    try:
        c.execute("SELECT sys_id, user_name, first_name, title, introduction, city, department, active FROM sys_user")
        rows = c.fetchall()
        for r in rows:
            sys_id = r[0]
            # user_name -> sys_class_name, wait. first_name = call sign
            name = r[2] or r[1]
            short_description = r[3]
            u_system_prompt = r[4]
            assigned_to = r[5] # city
            u_llm_engine = r[6] # department
            active = r[7]

            c.execute("INSERT OR IGNORE INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to) VALUES (?, ?, 'cmdb_ci_ai_persona', ?, ?, ?)",
                (sys_id, name, short_description, active, assigned_to))
            
            c.execute("INSERT OR IGNORE INTO cmdb_ci_ai_persona (sys_id, u_system_prompt, u_deployment_zone, u_boggs_reactivity, u_cadence) VALUES (?, ?, ?, 'medium', 'pacer')",
                (sys_id, u_system_prompt, ''))

    except Exception as e:
        print("Couldn't pull from sys_user:", e)
        # Try from personas.json
        with open("/home/james/stacklabs/01_Sovereign_Portal/public/personas.json", "r") as f:
            personas = json.load(f)
            for p in personas:
                sys_id = p.get('id', uuid.uuid4().hex)
                name = p.get('name', 'Unknown')
                prompt = p.get('u_system_prompt', '')
                team = p.get('team', '')
                zone = p.get('u_deployment_zone', '')
                c.execute("INSERT OR IGNORE INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to) VALUES (?, ?, 'cmdb_ci_ai_persona', '', 1, ?)",
                    (sys_id, name, team))
                c.execute("INSERT OR IGNORE INTO cmdb_ci_ai_persona (sys_id, u_system_prompt, u_deployment_zone, u_boggs_reactivity, u_cadence) VALUES (?, ?, ?, ?, ?)",
                    (sys_id, prompt, zone, p.get('u_boggs_reactivity', ''), p.get('u_cadence', '')))

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
