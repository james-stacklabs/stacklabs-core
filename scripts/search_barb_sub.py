import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cur.fetchall()]

for table in tables:
    try:
        cur.execute(f"PRAGMA table_info({table});")
        columns = [col[1] for col in cur.fetchall()]
        for col in columns:
            query = f"SELECT DISTINCT {col} FROM {table} WHERE CAST({col} AS TEXT) LIKE '%barb%'"
            cur.execute(query)
            matches = [r[0] for r in cur.fetchall() if r[0] is not None]
            if matches:
                print(f"Table '{table}', Column '{col}' contains matches: {matches}")
    except Exception as e:
        print(f"Error in {table}: {e}")

conn.close()
