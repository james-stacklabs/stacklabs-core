import sqlite3

db_path = "/home/james/stacklabs/dna/sovereign_now.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]

search_terms = ["UNHINGEDCONVENIENCE", "MADAME MAYHEM"]

for table in tables:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    
    for col in columns:
        try:
            for term in search_terms:
                query = f"SELECT * FROM {table} WHERE UPPER(CAST({col} AS TEXT)) LIKE ?"
                cursor.execute(query, (f"%{term}%",))
                records = cursor.fetchall()
                if records:
                    print(f"[{table}].{col} contains '{term}':")
                    for r in records[:5]:
                        print("  -", r)
        except Exception as e:
            pass

conn.close()
