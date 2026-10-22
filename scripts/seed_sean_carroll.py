#!/usr/bin/env python3
import sqlite3
import uuid

HISTORICAL_DB = "/home/james/sovereign_inbox/executed/sovereign_now_historical_backup.db"
ACTIVE_DB = "/home/james/stacklabs/dna/sovereign_now.db"

def main():
    print("[*] Seeding sean_carroll from historical backup...")
    h_conn = sqlite3.connect(HISTORICAL_DB)
    h_cur = h_conn.cursor()
    
    # Get columns of persona in active database to make a safe query
    a_conn = sqlite3.connect(ACTIVE_DB)
    a_cur = a_conn.cursor()
    
    # Let's read sean_carroll's data from historical DB
    h_cur.execute("SELECT * FROM persona WHERE user_name = 'sean_carroll'")
    row = h_cur.fetchone()
    if not row:
        print("[!] Error: sean_carroll not found in historical database!")
        h_conn.close()
        a_conn.close()
        return

    # Let's get column names of persona table in historical database
    h_cur.execute("PRAGMA table_info(persona)")
    h_cols = [col[1] for col in h_cur.fetchall()]
    
    # Let's get column names of persona table in active database
    a_cur.execute("PRAGMA table_info(persona)")
    a_cols = [col[1] for col in a_cur.fetchall()]
    
    # Map values from historical row to active table columns
    h_data = dict(zip(h_cols, row))
    
    # Construct insert columns and values
    insert_cols = []
    insert_vals = []
    for col in a_cols:
        if col in h_data:
            insert_cols.append(col)
            insert_vals.append(h_data[col])
        elif col == 'cadence':
            # Cadence is a yapper as defined in user request
            insert_cols.append('cadence')
            insert_vals.append('yapper')
        elif col == 'team':
            insert_cols.append('team')
            insert_vals.append('Card Turpey')
        elif col == 'llm_engine':
            insert_cols.append('llm_engine')
            insert_vals.append('gemini-2.0-flash')

    # Ensure ID is present
    if 'id' not in insert_cols or not h_data.get('id'):
        if 'id' in insert_cols:
            idx = insert_cols.index('id')
            insert_vals[idx] = "persona_sean_carroll"
        else:
            insert_cols.append('id')
            insert_vals.append("persona_sean_carroll")
            
    placeholders = ",".join(["?"] * len(insert_vals))
    sql = f"INSERT OR REPLACE INTO persona ({','.join(insert_cols)}) VALUES ({placeholders})"
    
    a_cur.execute(sql, insert_vals)
    a_conn.commit()
    print("[+] Inserted/Replaced sean_carroll in active persona table.")
    
    # Let's reconcile sean_carroll in sys_user, cmdb_ci, cmdb_ci_ai_persona
    persona_id = h_data.get('id', 'persona_sean_carroll')
    display_name = h_data.get('display_name', 'Sean Carroll')
    system_prompt = h_data.get('system_prompt', '')
    deep_lore = h_data.get('deep_lore', '')
    avatar_url = h_data.get('avatar_url', '/avatars/sean_carroll/sean_carroll_avatar.png')
    color = h_data.get('color', '#0d9488')
    bio = h_data.get('behavior_notes', 'Founder of Card Turpey.')
    
    # 1. sys_user
    a_cur.execute("SELECT sys_id FROM sys_user WHERE user_name = 'sean_carroll'")
    u_row = a_cur.fetchone()
    if u_row:
        user_id = u_row[0]
        a_cur.execute("""
            UPDATE sys_user SET
                display_name = ?,
                first_name = 'Sean',
                last_name = 'Carroll',
                introduction = ?,
                department = 'Card Turpey',
                avatar_url = ?,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (display_name, bio, avatar_url, user_id))
    else:
        user_id = persona_id
        a_cur.execute("""
            INSERT INTO sys_user (sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url)
            VALUES (?, 'sean_carroll', 'Sean', 'Carroll', 'Advocate', ?, 'Card Turpey', 1, 'advocate', ?, ?)
        """, (user_id, bio, display_name, avatar_url))

    # 2. cmdb_ci
    a_cur.execute("SELECT sys_id FROM cmdb_ci WHERE name = 'sean_carroll'")
    ci_row = a_cur.fetchone()
    if ci_row:
        ci_id = ci_row[0]
        a_cur.execute("""
            UPDATE cmdb_ci SET
                assigned_to = 'Card Turpey',
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (ci_id,))
    else:
        a_cur.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_ai_persona', 'Card Turpey', 'Sovereign Entity', 1)
        """, (persona_id, 'sean_carroll'))

    # 3. cmdb_ci_ai_persona
    a_cur.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (persona_id,))
    ap_row = a_cur.fetchone()
    if ap_row:
        a_cur.execute("""
            UPDATE cmdb_ci_ai_persona SET
                u_system_prompt = ?,
                u_deep_lore = ?,
                u_deployment_zone = 'global',
                u_cadence = 'yapper'
            WHERE sys_id = ?
        """, (system_prompt, deep_lore, persona_id))
    else:
        a_cur.execute("""
            INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore)
            VALUES (?, 'medium', ?, 'global', 'yapper', ?)
        """, (persona_id, system_prompt, deep_lore))
        
    a_conn.commit()
    a_conn.close()
    h_conn.close()
    print("[✔] Onboarding complete for sean_carroll in all CMDB and User tables.")

if __name__ == "__main__":
    main()
