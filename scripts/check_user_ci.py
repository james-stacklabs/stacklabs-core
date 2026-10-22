import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
cur = conn.cursor()

cur.execute("SELECT * FROM cmdb_ci WHERE sys_id = '454f1a7b8cf2f0d82f7f980b9ebccb9b'")
print("Match in cmdb_ci:", cur.fetchall())

conn.close()
