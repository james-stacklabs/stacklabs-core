import sqlite3
import uuid

def sync():
    conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
    c = conn.cursor()
    
    # 1. Sync all cmdb_ci personas to sys_user
    c.execute("SELECT name, short_description, assigned_to FROM cmdb_ci WHERE sys_class_name = 'cmdb_ci_ai_persona'")
    personas = c.fetchall()
    
    for p in personas:
        name = p[0]
        desc = p[1]
        team = p[2]
        
        c.execute("SELECT sys_id FROM sys_user WHERE user_name = ? COLLATE NOCASE", (name,))
        if not c.fetchone():
            sys_id = uuid.uuid4().hex
            c.execute("INSERT INTO sys_user (sys_id, user_name, first_name, title, department, active, introduction) VALUES (?, ?, ?, ?, ?, 1, ?)",
                      (sys_id, name, name, desc, team, desc))
        else:
            c.execute("UPDATE sys_user SET active = 1 WHERE user_name = ? COLLATE NOCASE", (name,))
            
    conn.commit()
    print("Personas synced to sys_user.")

if __name__ == "__main__":
    sync()
