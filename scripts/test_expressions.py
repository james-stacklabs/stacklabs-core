import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM cmdb_ci_expression_avatar;")
for r in cur.fetchall():
    print(dict(r))
conn.close()
