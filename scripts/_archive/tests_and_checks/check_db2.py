import sqlite3
conn = sqlite3.connect('/home/james/stacklabs/04_Sovereign_Core/sovereign_core.db', timeout=10)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables:", cursor.fetchall())
