import sqlite3
try:
    conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db', timeout=10)
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(sys_user);')
    print("SYS_USER:", cursor.fetchall())
    
    cursor.execute('PRAGMA table_info(cmdb_ci);')
    print("CMDB_CI:", cursor.fetchall())
    conn.close()
except Exception as e:
    print(e)
