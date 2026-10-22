#!/usr/bin/env python3
# /home/james/stacklabs/scripts/purge_and_archive.py
import sqlite3
import json
import os

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ARCHIVE_PATH = "/home/james/sovereign_inbox/archives/tickets_archive_prestige.json"
os.makedirs(os.path.dirname(ARCHIVE_PATH), exist_ok=True)

con = sqlite3.connect(DB_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Query all existing tasks from the live sovereign_tickets table
cur.execute("SELECT * FROM sovereign_tickets")
all_tasks = [dict(r) for r in cur.fetchall()]

# Filter: Exclude duplicates and generic "Semantically Routed Document" entries from sovereign_tickets,
# keeping only unique developer-written tickets or completed system stories (prestige)
prestige_tasks = []
seen_descriptions = set()

for task in all_tasks:
    desc = task.get("short_description", "")
    task_id = str(task.get("task_id") or task.get("number") or task.get("sys_id") or "")
    
    # Keep completed system-level STRY or INC tickets that aren't loop duplicates
    if "Semantically Routed Document" not in desc:
        prestige_tasks.append(task)
    elif "Laundry" in task_id or "Dryer" in task_id:
        # Keep exactly one laundry ticket (e.g., INC2556327) for UAT prestige record
        if "laundry_uat" not in seen_descriptions:
            prestige_tasks.append(task)
            seen_descriptions.add("laundry_uat")

# Save the filtered prestige log
with open(ARCHIVE_PATH, "w") as f:
    json.dump(prestige_tasks, f, indent=2)

# Clear both the borked active dashboard and SDLC tables to start fresh
cur.execute("DELETE FROM sovereign_tickets")
cur.execute("DELETE FROM sys_sdlc_task")
con.commit()
con.close()

print(f"🧹 Purged sovereign_tickets and sys_sdlc_task. Prestige archive saved with {len(prestige_tasks)} records.")
