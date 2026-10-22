import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ARCHIVE_DIR = "/home/james/sovereign_inbox/archives"

os.makedirs(ARCHIVE_DIR, exist_ok=True)
con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Query all existing tickets
cur.execute("SELECT * FROM sys_sdlc_task")
rows = [dict(r) for r in cur.fetchall()]
con.close()

# Save as formatted JSON
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
archive_path = os.path.join(ARCHIVE_DIR, f"tickets_archive_{timestamp}.json")

with open(archive_path, "w") as f:
    json.dump(rows, f, indent=2)

print(f"✅ Success: Archived {len(rows)} tickets to {archive_path}")
