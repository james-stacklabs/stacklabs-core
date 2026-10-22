#!/usr/bin/env python3
"""
Migration: Ensure cmdb_ci_fanstack_room and cmdb_ci_ai_persona have required columns.
Path: /home/james/stacklabs/scripts/migrations/migrate_cmdb_ci_fanstack_room.py
"""
import os
import sys
import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def main():
    print(f"Connecting to {DB_PATH} with 60s timeout...")
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA busy_timeout = 60000")
    cur = conn.cursor()
    
    # 1. cmdb_ci_fanstack_room
    cur.execute("PRAGMA table_info(cmdb_ci_fanstack_room)")
    existing_cols_room = {col[1]: col[2] for col in cur.fetchall()}
    
    expected_cols_room = {
        "u_cadence": "TEXT DEFAULT 'pacer'",
        "cadence": "TEXT DEFAULT 'pacer'",
        "boggs_level": "INTEGER DEFAULT 3",
        "room_state": "TEXT DEFAULT 'active'",
        "website_purpose": "TEXT",
        "website_domain": "TEXT",
        "website_pages": "TEXT",
        "website_features": "TEXT",
        "website_colors": "TEXT",
        "website_typography": "TEXT",
        "website_additional_requirements": "TEXT"
    }
    
    for col_name, col_def in expected_cols_room.items():
        if col_name not in existing_cols_room:
            print(f"Adding column '{col_name}' to cmdb_ci_fanstack_room...")
            cur.execute(f"ALTER TABLE cmdb_ci_fanstack_room ADD COLUMN {col_name} {col_def}")
            conn.commit()
            
    # 2. cmdb_ci_ai_persona
    cur.execute("PRAGMA table_info(cmdb_ci_ai_persona)")
    existing_cols_persona = {col[1]: col[2] for col in cur.fetchall()}
    
    expected_cols_persona = {
        "u_system_prompt": "TEXT",
        "u_deployment_zone": "TEXT",
        "u_boggs_reactivity": "TEXT",
        "u_cadence": "TEXT DEFAULT 'pacer'",
        "u_deep_lore": "TEXT",
        "u_governance_boundaries": "TEXT",
        "u_avatar_prompt": "TEXT",
        "u_llm_engine": "TEXT"
    }
    
    for col_name, col_def in expected_cols_persona.items():
        if col_name not in existing_cols_persona:
            print(f"Adding column '{col_name}' to cmdb_ci_ai_persona...")
            cur.execute(f"ALTER TABLE cmdb_ci_ai_persona ADD COLUMN {col_name} {col_def}")
            conn.commit()

    # Backfill u_ columns from existing columns in cmdb_ci_ai_persona
    cur.execute("""
        UPDATE cmdb_ci_ai_persona
        SET 
            u_system_prompt = COALESCE(u_system_prompt, system_prompt),
            u_deployment_zone = COALESCE(u_deployment_zone, deployment_zone),
            u_boggs_reactivity = COALESCE(u_boggs_reactivity, boggs_reactivity),
            u_cadence = COALESCE(u_cadence, cadence),
            u_deep_lore = COALESCE(u_deep_lore, deep_lore),
            u_governance_boundaries = COALESCE(u_governance_boundaries, governance_boundaries),
            u_avatar_prompt = COALESCE(u_avatar_prompt, avatar_prompt)
    """)
    conn.commit()

    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    main()
