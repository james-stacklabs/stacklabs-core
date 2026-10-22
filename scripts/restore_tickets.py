#!/usr/bin/env python3
import sqlite3
import re
import os

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
LEDGER_PATH = "/home/james/stacklabs/dna/notebook_lm_exports/SOVEREIGN_OS_INTERNAL_MASSIVE_DATA_TRANSFER_PACKAGE.md"

def restore_tickets():
    if not os.path.exists(LEDGER_PATH):
        print(f"❌ Ledger not found at {LEDGER_PATH}")
        return
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    # 1. Parse the ledger for resolved tickets
    resolved_tickets = {}
    ticket_pattern = re.compile(r"^\|\s*([A-Za-z0-9\-_]+)\s*\|\s*[A-Za-z]+\s*\|\s*Resolved\s*\|\s*([^|]+)", re.IGNORECASE)
    
    with open(LEDGER_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = ticket_pattern.match(line)
            if m:
                resolved_tickets[m.group(1).strip()] = m.group(2).strip()
                
    print(f"Loaded {len(resolved_tickets)} resolved tickets from historical ledger.")

    # 2. Connect to the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Query currently staged tickets (state = 1)
    cursor.execute("SELECT number, short_description, state, cmdb_ci FROM sovereign_tickets WHERE state = 1")
    staged_tickets = cursor.fetchall()

    print(f"\nAnalyzing {len(staged_tickets)} currently staged tickets...")
    restored_count = 0
    
    for number, short_desc, state, cmdb_ci in staged_tickets:
        if number in resolved_tickets:
            print(f"  [RESTORE] {number} | {short_desc} (Setting state = 4 / RESOLVED)")
            
            # Update sovereign_tickets
            cursor.execute("""
                UPDATE sovereign_tickets 
                SET state = 4, work_notes = 'Restored to RESOLVED state post sync sweep.' 
                WHERE number = ?
            """, (number,))
            
            # Update sys_sdlc_task
            cursor.execute("""
                UPDATE sys_sdlc_task 
                SET state = 'RESOLVED' 
                WHERE task_id = ?
            """, (number,))
            
            restored_count += 1

    conn.commit()
    conn.close()
    print(f"\n✅ Successfully restored {restored_count} tickets to RESOLVED status in the database.")

if __name__ == "__main__":
    restore_tickets()
