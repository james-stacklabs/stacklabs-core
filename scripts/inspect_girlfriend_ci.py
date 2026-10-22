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

print_query("SELECT sys_id, name, sys_class_name FROM cmdb_ci WHERE sys_class_name LIKE '%girl%' OR name LIKE '%girl%' OR name = 'barb'", "CIs with girl or barb")
print_query("SELECT DISTINCT sys_class_name FROM cmdb_ci", "Distinct CI classes")

conn.close()
