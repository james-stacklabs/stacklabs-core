#!/usr/bin/env python3
import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

conn = sqlite3.connect(DB_PATH, timeout=60.0)
cur = conn.cursor()
cur.execute("PRAGMA table_info(cmdb_ci_ai_persona)")
cols = cur.fetchall()
print("cmdb_ci_ai_persona columns:")
for col in cols:
    print(col)

conn.close()
