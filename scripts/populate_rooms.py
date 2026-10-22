import sqlite3
import uuid

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

# Mean Gene is a SYSTEM_MODERATOR subroutine, not a human user.
SUBROUTINE_PERSONAS = {'mean_gene'}

def populate():
    print("[*] Populating canonical personas...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # The six canonical personas
    six_personas = ['dot', 'barf', 'wardy', 'tomahawk', 'phanatic', 'mean_gene']

    for p_name in six_personas:
        # Map wardy to wordy_nym in the persona table
        db_p_name = 'wordy_nym' if p_name == 'wardy' else p_name
        
        c.execute("""
            SELECT id, display_name, team, system_prompt, boggs_level, deep_lore, behavior_notes, color, avatar_url, cadence
            FROM persona 
            WHERE user_name=?
        """, (db_p_name,))
        p_row = c.fetchone()
        
        if not p_row:
            print(f"[populate_rooms] Warning: Persona {db_p_name} not found in persona table!")
            continue
            
        sys_id, display_name, team, system_prompt, boggs_level, deep_lore, behavior_notes, color, avatar_url, cadence = p_row
        is_subroutine = p_name in SUBROUTINE_PERSONAS

        # 1. Update/Insert in sys_user (skip for subroutine personas)
        if not is_subroutine:
            c.execute("SELECT sys_id FROM sys_user WHERE user_name=?", (p_name,))
            user_row = c.fetchone()
            if not user_row:
                c.execute("""
                    INSERT INTO sys_user (sys_id, user_name, first_name, title, department, introduction, active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (sys_id, p_name, display_name, f"AI Advocate - {team}", team, deep_lore))
                print(f"  Inserted canonical {p_name} into sys_user.")
            else:
                c.execute("""
                    UPDATE sys_user 
                    SET first_name=?, title=?, department=?, introduction=?, active=1
                    WHERE user_name=?
                """, (display_name, f"AI Advocate - {team}", team, deep_lore, p_name))
                print(f"  Updated canonical {p_name} in sys_user.")

        # 2. Update/Insert in cmdb_ci
        c.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id=?", (sys_id,))
        if not c.fetchone():
            c.execute("""
                INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
                VALUES (?, ?, 'cmdb_ci_ai_persona', ?, ?, 1)
            """, (sys_id, p_name, team, f"AI Advocate - {display_name}"))
            print(f"  Inserted canonical {p_name} into cmdb_ci.")
        else:
            c.execute("""
                UPDATE cmdb_ci 
                SET name=?, assigned_to=?, short_description=?, operational_status=1
                WHERE sys_id=?
            """, (p_name, team, f"AI Advocate - {display_name}", sys_id))
            print(f"  Updated canonical {p_name} in cmdb_ci.")

        # 3. Update/Insert in cmdb_ci_ai_persona
        c.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id=?", (sys_id,))
        if not c.fetchone():
            c.execute("""
                INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence)
                VALUES (?, ?, ?, ?, ?)
            """, (sys_id, boggs_level or 'medium', system_prompt or deep_lore, team or 'global', cadence or 'pacer'))
            print(f"  Inserted canonical {p_name} into cmdb_ci_ai_persona.")
        else:
            c.execute("""
                UPDATE cmdb_ci_ai_persona 
                SET u_boggs_reactivity=?, u_system_prompt=?, u_deployment_zone=?, u_cadence=?
                WHERE sys_id=?
            """, (boggs_level or 'medium', system_prompt or deep_lore, team or 'global', cadence or 'pacer', sys_id))
            print(f"  Updated canonical {p_name} in cmdb_ci_ai_persona.")

    conn.commit()
    conn.close()
    print("✅ Canonical personas populated successfully.")

if __name__ == '__main__':
    populate()
