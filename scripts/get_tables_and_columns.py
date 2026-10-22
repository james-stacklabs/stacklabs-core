import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cur.fetchall()]

for t in tables:
    if 'hardware' in t.lower() or 'expression' in t.lower() or 'avatar' in t.lower() or 'stack' in t.lower():
        print(f"\n===== Table {t} =====")
        cur.execute(f"PRAGMA table_info({t});")
        for col in cur.fetchall():
            print(f"  {col[1]} ({col[2]})")
        try:
            cur.execute(f"SELECT * FROM {t} LIMIT 5;")
            rows = cur.fetchall()
            if rows:
                print(f"  Sample rows:")
                for r in rows:
                    print(f"    {r}")
        except Exception as e:
            print(f"  Error reading: {e}")

conn.close()
