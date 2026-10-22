import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cur.fetchall()]

search_values = ['7e8345ad935d4d619c8dc1e15c494d64', '4559cbf4-dfb5-47a1-a814-192f9e9cc803', 'barbara', 'barbara_ci']

for table in tables:
    try:
        cur.execute(f"PRAGMA table_info({table});")
        columns = [col[1] for col in cur.fetchall()]
        for col in columns:
            for val in search_values:
                query = f"SELECT count(*) FROM {table} WHERE CAST({col} AS TEXT) = ?"
                cur.execute(query, (val,))
                count = cur.fetchone()[0]
                if count > 0:
                    print(f"Exact Match in '{table}', Column '{col}': {count} occurrences of '{val}'")
    except Exception as e:
        print(f"Error querying table {table}: {e}")

conn.close()
