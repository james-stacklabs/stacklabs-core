import sqlite3
import os

dbs = [
    "/home/james/stacklabs/sovereign_now.db",
    "/home/james/stacklabs/data/sovereign_now.db",
    "/home/james/stacklabs/15_FanStack/sovereign_now.db",
    "/home/james/stacklabs/dna/sovereign_now.db",
    "/home/james/stacklabs/20_AetherVet/sovereign_now.db",
    "/home/james/stacklabs/01_Sovereign_Portal/sovereign_now.db",
]

search_vals = ['barbara', 'barbara_ci', '7e8345ad935d4d619c8dc1e15c494d64', '4559cbf4-dfb5-47a1-a814-192f9e9cc803']

for db_path in dbs:
    if not os.path.exists(db_path):
        continue
    print(f"\n===== Checking DB: {db_path} =====")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    for table in tables:
        try:
            cur.execute(f"PRAGMA table_info({table});")
            columns = [col[1] for col in cur.fetchall()]
            for col in columns:
                if col in ('user_name', 'id', 'sys_id', 'name', 'username'):
                    for val in search_vals:
                        query = f"SELECT {col} FROM {table} WHERE {col} = ?"
                        cur.execute(query, (val,))
                        res = cur.fetchall()
                        if res:
                            print(f"  Table '{table}', Col '{col}': found {res}")
        except Exception as e:
            pass
    conn.close()
