import sqlite3
conn = sqlite3.connect('/home/james/stacklabs/04_Sovereign_Core/sovereign_core.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", tables)
for t in tables:
    tname = t[0]
    cursor.execute(f"SELECT COUNT(*) FROM {tname}")
    count = cursor.fetchone()[0]
    print(f"Table {tname}: {count} rows")
