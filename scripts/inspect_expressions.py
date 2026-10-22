import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
cur = conn.cursor()

cur.execute("SELECT * FROM cmdb_ci_expression_avatar LIMIT 20;")
cols = [d[0] for d in cur.description]
print("\t".join(cols))
for r in cur.fetchall():
    print("\t".join(str(x) for x in r))

conn.close()
