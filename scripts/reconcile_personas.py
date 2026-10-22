#!/usr/bin/env python3
import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
TARGET_PERSONAS = [
    'keith_fanboy', 'UncleStevieStan', '7_train_terry', 'barf',
    'Friar_Frank', 'Petco_Paul', 'Tacos_N_Tatis', 'Slam_Diego_Surfer',
    'Gwynn_Ghost', 'spin_rate_sylvia', 'compliance_karen', 'dr_terp',
    'ed_haskins', 'lupita_community'
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("🔄 Starting Persona database reconciliation...")
    
    for username in TARGET_PERSONAS:
        # Retrieve persona details (case-insensitive username search)
        cur.execute("SELECT id, user_name, display_name, team, system_prompt, deep_lore, avatar_url, cadence, boggs_level, behavior_notes FROM persona WHERE LOWER(user_name) = LOWER(?)", (username,))
        row = cur.fetchone()
        if not row:
            print(f"⚠️ Warning: Persona '{username}' not found in persona table! Skipping reconciliation.")
            continue
            
        sys_id, canonical_username, display_name, team, system_prompt, deep_lore, avatar_url, cadence, boggs_level, behavior_notes = row
        bio = behavior_notes if behavior_notes else f"Brand Advocate for {team}."
        
        name_parts = display_name.split(" ")
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # 1. Reconcile sys_user (match on sys_id or username case-insensitively)
        cur.execute("SELECT sys_id FROM sys_user WHERE sys_id = ? OR LOWER(user_name) = LOWER(?)", (sys_id, canonical_username))
        user_row = cur.fetchone()
        if user_row:
            user_id = user_row[0]
            print(f"  [{canonical_username}] sys_user exists (ID: {user_id}). Updating...")
            cur.execute("""
                UPDATE sys_user SET
                    user_name = ?,
                    first_name = ?,
                    last_name = ?,
                    introduction = ?,
                    department = ?,
                    display_name = ?,
                    avatar_url = ?,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (canonical_username, first_name, last_name, bio, team, display_name, avatar_url, user_id))
        else:
            print(f"  [{canonical_username}] sys_user missing. Inserting...")
            cur.execute("""
                INSERT INTO sys_user (
                    sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
                ) VALUES (?, ?, ?, ?, 'Advocate', ?, ?, 1, 'advocate', ?, ?)
            """, (sys_id, canonical_username, first_name, last_name, bio, team, display_name, avatar_url))
            
        # 2. Reconcile cmdb_ci (match on sys_id or name case-insensitively)
        cur.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ? OR LOWER(name) = LOWER(?)", (sys_id, canonical_username))
        ci_row = cur.fetchone()
        if ci_row:
            ci_id = ci_row[0]
            print(f"  [{canonical_username}] cmdb_ci exists (ID: {ci_id}). Updating...")
            cur.execute("""
                UPDATE cmdb_ci SET
                    name = ?,
                    assigned_to = ?,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (canonical_username, team, ci_id))
        else:
            print(f"  [{canonical_username}] cmdb_ci missing. Inserting...")
            cur.execute("""
                INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
                VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 'Sovereign Entity', 1)
            """, (sys_id, canonical_username, team))
            
        # 3. Reconcile cmdb_ci_ai_persona
        cur.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
        ap_row = cur.fetchone()
        
        # Determine u_deployment_zone from team/username
        u_deployment_zone = "global"
        if team == "SPITESLICE":
            u_deployment_zone = "SPITESLICE_ZONE"
        elif team == "CARYGRANTINVESTIGATIONS":
            u_deployment_zone = "CARYGRANT_ZONE"
            
        if ap_row:
            print(f"  [{canonical_username}] cmdb_ci_ai_persona exists (ID: {sys_id}). Updating...")
            cur.execute("""
                UPDATE cmdb_ci_ai_persona SET
                    u_system_prompt = ?,
                    u_deep_lore = ?,
                    u_deployment_zone = ?,
                    u_cadence = ?
                WHERE sys_id = ?
            """, (system_prompt, deep_lore, u_deployment_zone, cadence, sys_id))
        else:
            print(f"  [{canonical_username}] cmdb_ci_ai_persona missing. Inserting...")
            cur.execute("""
                INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore)
                VALUES (?, 'medium', ?, ?, ?, ?)
            """, (sys_id, system_prompt, u_deployment_zone, cadence, deep_lore))
            
    conn.commit()
    conn.close()
    print("✅ Roster databases reconciled and synchronized successfully!")

if __name__ == "__main__":
    main()
