#!/usr/bin/env python3
import sqlite3
import subprocess
import re

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def clean_database():
    conn = sqlite3.connect(DB_PATH)
    # Register REGEXP function in SQLite
    conn.create_function("regexp", 2, lambda x, y: 1 if (y and re.search(x, y)) else 0)
    cursor = conn.cursor()

    print("🧹 Cleaning duplicate UncleStevieStan records...")

    # Canonical UncleStevieStan ID: b4b7157a986443ada218c9a393b00b77
    duplicate_ids = ['0ac7f5043fdc4f2a92a96290b0ac5c1a', 'persona_unclesteviestan']
    duplicate_sys_users = ['9a0d9a79-6a0f-4e9d-a01f-784651544f1a', 'unclesteviestan']

    for dup_id in duplicate_ids:
        print(f"  Deleting duplicate ID: {dup_id}")
        cursor.execute("DELETE FROM persona WHERE id = ?", (dup_id,))
        cursor.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (dup_id,))
        cursor.execute("DELETE FROM cmdb_ci_ai_persona WHERE sys_id = ?", (dup_id,))
        cursor.execute("DELETE FROM cmdb_ci_persona WHERE sys_id = ?", (dup_id,))
        cursor.execute("DELETE FROM sys_user WHERE sys_id = ?", (dup_id,))
        cursor.execute("DELETE FROM game_persona WHERE persona_id = ?", (dup_id,))
        cursor.execute("DELETE FROM m2m_persona_room WHERE persona = ? OR sys_id = ?", (dup_id, dup_id))

    for dup_user in duplicate_sys_users:
        cursor.execute("DELETE FROM sys_user WHERE sys_id = ? OR user_name = ?", (dup_user, dup_user))

    print("🧹 Purging empty-prompt stubs created on 2026-06-03...")

    cursor.execute("""
        SELECT id, user_name FROM persona 
        WHERE (system_prompt IS NULL OR LENGTH(TRIM(system_prompt)) = 0)
    """)
    stubs = cursor.fetchall()

    for stub_id, username in stubs:
        cursor.execute("SELECT id FROM persona WHERE user_name = ? AND id != ?", (username, stub_id))
        canonicals = cursor.fetchall()
        
        if canonicals or stub_id.startswith('persona_'):
            print(f"  Purging stub: {username} (ID: {stub_id})")
            cursor.execute("DELETE FROM persona WHERE id = ?", (stub_id,))
            cursor.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (stub_id,))
            cursor.execute("DELETE FROM cmdb_ci_ai_persona WHERE sys_id = ?", (stub_id,))
            cursor.execute("DELETE FROM cmdb_ci_persona WHERE sys_id = ?", (stub_id,))
            cursor.execute("DELETE FROM sys_user WHERE sys_id = ? OR user_name = ?", (stub_id, username))
            cursor.execute("DELETE FROM game_persona WHERE persona_id = ?", (stub_id,))
            cursor.execute("DELETE FROM m2m_persona_room WHERE persona = ? OR sys_id = ?", (stub_id, stub_id))

    # 1. Purge room-appended clone users from sys_user
    print("🧹 Purging room-appended clone users from sys_user...")
    cursor.execute("SELECT sys_id, user_name FROM sys_user WHERE user_name REGEXP '_\\d{6}$'")
    sys_users_to_delete = cursor.fetchall()
    print(f"  Found {len(sys_users_to_delete)} clone users in sys_user.")
    
    for sys_id, user_name in sys_users_to_delete:
        cursor.execute("DELETE FROM sys_user WHERE sys_id = ?", (sys_id,))
        cursor.execute("DELETE FROM game_persona WHERE persona_id = ?", (sys_id,))
        cursor.execute("DELETE FROM m2m_persona_room WHERE persona = ? OR sys_id = ?", (sys_id, sys_id))

    # 2. Purge room-appended clone records from persona table
    print("🧹 Purging room-appended clone records from persona...")
    cursor.execute("SELECT id, user_name FROM persona WHERE user_name REGEXP '_\\d{6}$'")
    personas_to_delete = cursor.fetchall()
    print(f"  Found {len(personas_to_delete)} clone records in persona.")
    
    for sys_id, user_name in personas_to_delete:
        cursor.execute("DELETE FROM persona WHERE id = ?", (sys_id,))
        cursor.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
        cursor.execute("DELETE FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
        cursor.execute("DELETE FROM cmdb_ci_persona WHERE sys_id = ?", (sys_id,))
        cursor.execute("DELETE FROM game_persona WHERE persona_id = ?", (sys_id,))
        cursor.execute("DELETE FROM m2m_persona_room WHERE persona = ? OR sys_id = ?", (sys_id, sys_id))

    # 3. Purge clone records from cmdb_ci
    print("🧹 Purging remaining clone records from cmdb_ci...")
    cursor.execute("SELECT sys_id, name FROM cmdb_ci WHERE name REGEXP '_\\d{6}$'")
    cmdb_cis_to_delete = cursor.fetchall()
    print(f"  Found {len(cmdb_cis_to_delete)} clone records in cmdb_ci.")
    
    for sys_id, name in cmdb_cis_to_delete:
        cursor.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
        cursor.execute("DELETE FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
        cursor.execute("DELETE FROM cmdb_ci_persona WHERE sys_id = ?", (sys_id,))

    conn.commit()
    conn.close()
    print("✅ Database cleanup transaction complete.")

def verify_seating():
    print("🔄 Re-initializing room 823619 seating...")
    try:
        subprocess.run([
            "python3", "scripts/setup_all_rooms.py", "823619"
        ], check=True)
        print("✅ Seating setup run complete.")
    except Exception as e:
        print(f"⚠️ Error running room setup: {e}")

if __name__ == "__main__":
    clean_database()
    verify_seating()
