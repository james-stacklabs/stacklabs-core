import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
cur = conn.cursor()
cur.execute("SELECT name, sys_class_name, assigned_to FROM cmdb_ci WHERE sys_class_name='cmdb_ci_ai_persona';")
for r in cur.fetchall():
    print(r)
conn.close()
