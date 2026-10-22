import sqlite3
import os

DB_PATH = "/home/james/stacklabs/04_Sovereign_Core/sovereign_core.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sam_tracker_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    message TEXT NOT NULL
)
""")
conn.commit()
conn.close()
print("Table sam_tracker_log initialized.")
