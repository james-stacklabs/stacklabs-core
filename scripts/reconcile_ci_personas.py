import sqlite3

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def main():
    print("[*] Starting database reconciliation for personas...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Update team assignment for canonical personas based on cmdb_ci.assigned_to
    cursor.execute("""
        SELECT p.id, p.user_name, c.assigned_to 
        FROM persona p
        JOIN cmdb_ci c ON p.id = c.sys_id
        WHERE p.user_name NOT LIKE '%_ci'
          AND c.assigned_to IS NOT NULL 
          AND c.assigned_to != ''
    """)
    canonical_rows = cursor.fetchall()
    
    updated_teams_count = 0
    for r in canonical_rows:
        pid = r['id']
        uname = r['user_name']
        team = r['assigned_to']
        
        cursor.execute("UPDATE persona SET team = ? WHERE id = ?", (team, pid))
        updated_teams_count += 1
        
    print(f"[*] Updated team field for {updated_teams_count} canonical personas based on CMDB mapping.")

    # 2. Sync master prompts/details from canonical personas to their _ci duplicates in the persona table
    cursor.execute("""
        SELECT id, user_name, team, system_prompt, boggs_level, color, cadence, deep_lore, behavior_notes, governance
        FROM persona
        WHERE user_name NOT LIKE '%_ci'
    """)
    all_canonicals = cursor.fetchall()
    
    synced_ci_count = 0
    for canon in all_canonicals:
        canon_name = canon['user_name']
        ci_name = f"{canon_name}_ci"
        
        # Check if _ci replica exists
        cursor.execute("SELECT id FROM persona WHERE user_name = ?", (ci_name,))
        ci_row = cursor.fetchone()
        if ci_row:
            ci_id = ci_row['id']
            cursor.execute("""
                UPDATE persona SET
                    system_prompt = ?,
                    boggs_level = ?,
                    color = ?,
                    cadence = ?,
                    deep_lore = ?,
                    behavior_notes = ?,
                    governance = ?
                WHERE id = ?
            """, (
                canon['system_prompt'],
                canon['boggs_level'],
                canon['color'],
                canon['cadence'],
                canon['deep_lore'],
                canon['behavior_notes'],
                canon['governance'],
                ci_id
            ))
            synced_ci_count += 1

    print(f"[*] Synchronized fields from canonical to _ci duplicates for {synced_ci_count} personas.")
    
    conn.commit()
    conn.close()
    print("[*] Reconciliation complete.")

if __name__ == "__main__":
    main()
