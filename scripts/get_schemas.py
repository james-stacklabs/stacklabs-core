import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
cur = conn.cursor()

tables = ["cmdb_ci", "persona", "cmdb_ci_ai_persona", "cmdb_ci_expression_avatar"]

for t in tables:
    print(f"\n===== SCHEMA FOR {t} =====")
    try:
        cur.execute(f"PRAGMA table_info({t});")
        for col in cur.fetchall():
            print(f"  {col[1]} ({col[2]})")
    except Exception as e:
        print(f"Error: {e}")

conn.close()
