import sqlite3

def empty_rooms():
    db_path = '/home/james/stacklabs/dna/sovereign_now.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        # Reset all personas to the bench
        c.execute("UPDATE cmdb_ci_ai_persona SET u_deployment_zone = 'BENCHED'")

        # Clear the persona-to-room mappings
        c.execute("DELETE FROM m2m_persona_room")

        # Identify room groups and clear their members to ensure no personas are attached
        c.execute("SELECT sys_id FROM sys_user_group WHERE name LIKE 'Game %'")
        groups = c.fetchall()
        for g in groups:
            c.execute("DELETE FROM sys_user_grmember WHERE group_id = ?", (g[0],))

        conn.commit()
        print("Successfully emptied all rooms. Personas are benched.")
    except Exception as e:
        print(f"Error emptying rooms: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    empty_rooms()
