import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
cur = conn.cursor()

def print_query(q, title):
    print(f"\n--- {title} ---")
    try:
        cur.execute(q)
        cols = [d[0] for d in cur.description]
        print("\t".join(cols))
        for r in cur.fetchall():
            print("\t".join(str(x) for x in r))
    except Exception as e:
        print(f"Error: {e}")

print_query("SELECT sys_id, name, sys_class_name, operational_status FROM cmdb_ci WHERE name LIKE '%barb%'", "cmdb_ci records containing 'barb'")
print_query("SELECT id, user_name, display_name, u_visual_style, team FROM persona WHERE user_name LIKE '%barb%'", "persona records containing 'barb'")
print_query("SELECT sys_id, u_visual_style FROM cmdb_ci_ai_persona WHERE sys_id IN (SELECT sys_id FROM cmdb_ci WHERE name LIKE '%barb%')", "cmdb_ci_ai_persona records containing 'barb'")
print_query("SELECT sys_id, user_name, first_name, last_name, active FROM sys_user WHERE user_name LIKE '%barb%'", "sys_user records containing 'barb'")

conn.close()
