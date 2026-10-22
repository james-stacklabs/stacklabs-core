#!/usr/bin/env python3
import sqlite3
import uuid

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
    
    print("🔄 Reconciling sim_agents table...")
    
    for username in TARGET_PERSONAS:
        # Retrieve persona details
        cur.execute("SELECT id, team FROM persona WHERE LOWER(user_name) = LOWER(?)", (username,))
        row = cur.fetchone()
        if not row:
            continue
            
        persona_id, team = row
        
        # Check if exists in sim_agents
        cur.execute("SELECT sys_id FROM sim_agents WHERE LOWER(persona_name) = LOWER(?)", (username,))
        sim_row = cur.fetchone()
        if sim_row:
            print(f"  [{username}] sim_agents entry exists (ID: {sim_row[0]}). Updating team...")
            cur.execute("UPDATE sim_agents SET team = ?, sys_updated_on = CURRENT_TIMESTAMP WHERE sys_id = ?", (team, sim_row[0]))
        else:
            sys_id = uuid.uuid4().hex
            print(f"  [{username}] sim_agents entry missing. Inserting...")
            cur.execute("""
                INSERT INTO sim_agents (sys_id, persona_name, team, injury_paranoia, transit_fatalism, asset_depreciation, tension)
                VALUES (?, ?, ?, 0.0, 0.0, 0.0, 0.0)
            """, (sys_id, username, team))
            
    conn.commit()
    conn.close()
    print("✅ sim_agents table reconciled and synchronized successfully!")

if __name__ == "__main__":
    main()
