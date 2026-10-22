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

print_query("SELECT * FROM cmdb_ci WHERE name LIKE '%barb%' OR sys_id IN ('287a773da7f9446880eadc797d165a16', '8bea7fb1511f4c9f8181c0b152b87999')", "cmdb_ci records details")
print_query("SELECT * FROM sys_user WHERE user_name = 'barb'", "sys_user barb details")

conn.close()
