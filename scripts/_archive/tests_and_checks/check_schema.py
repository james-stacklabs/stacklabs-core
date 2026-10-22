import sqlite3
conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(cmdb_ci_ai_persona);')
for row in cursor.fetchall(): print(row)
conn.close()
