import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("\n--- Querying cmdb_ci ---")
cur.execute("SELECT * FROM cmdb_ci WHERE sys_id IN ('7e8345ad935d4d619c8dc1e15c494d64', '4559cbf4-dfb5-47a1-a814-192f9e9cc803')")
for r in cur.fetchall():
    print(dict(r))

print("\n--- Querying cmdb_ci_ai_persona ---")
cur.execute("SELECT * FROM cmdb_ci_ai_persona WHERE sys_id IN ('7e8345ad935d4d619c8dc1e15c494d64', '4559cbf4-dfb5-47a1-a814-192f9e9cc803')")
for r in cur.fetchall():
    print(dict(r))

print("\n--- Querying sys_user ---")
cur.execute("SELECT * FROM sys_user WHERE user_name IN ('barbara', 'barbara_ci')")
for r in cur.fetchall():
    print(dict(r))

print("\n--- Querying persona ---")
cur.execute("SELECT * FROM persona WHERE id IN ('7e8345ad935d4d619c8dc1e15c494d64', '4559cbf4-dfb5-47a1-a814-192f9e9cc803') OR user_name IN ('barbara', 'barbara_ci')")
for r in cur.fetchall():
    print(dict(r))

conn.close()
