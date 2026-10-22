import sqlite3
import sys

DB_PATH = '/home/james/stacklabs/sovereign_intelligence.db'

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 1. Integrity check
    cur.execute("PRAGMA integrity_check;")
    result = cur.fetchone()[0]
    if result.lower() != 'ok':
        raise Exception(f"Database corruption detected: {result}")
        
    # 2. Check table and row counts
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='statcast_pitches';")
    if not cur.fetchone():
        raise Exception("Table 'statcast_pitches' is missing!")
        
    cur.execute("SELECT COUNT(*) FROM statcast_pitches;")
    row_count = cur.fetchone()[0]
    print(f"[VERIFIED] Database is healthy! Table 'statcast_pitches' has {row_count} rows.")
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"[CRITICAL ERROR] Database verification failed: {e}")
    sys.exit(1)
