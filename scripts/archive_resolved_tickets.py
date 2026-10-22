import sqlite3
import os
import shutil
import glob

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
INBOX_DIR = "/home/james/sovereign_inbox"
TICKETS_DIR = os.path.join(INBOX_DIR, "tickets")
ARCHIVE_DIR = os.path.join(INBOX_DIR, "executed")

def archive_resolved_tickets():
    if not os.path.exists(DB_PATH):
        print("⚠️ Database not found.")
        return
        
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # Query all tickets that are in state 4 (RESOLVED) or 5 (CLOSED)
    cur.execute("SELECT number FROM sovereign_tickets WHERE state IN (4, 5)")
    resolved_tickets = [row[0] for row in cur.fetchall()]
    con.close()
    
    print(f"⚡ Found {len(resolved_tickets)} resolved/closed tickets in DB.")
    
    archived_count = 0
    for ticket_num in resolved_tickets:
        # Search for files starting with WO-{number} or STRY-{number}
        # e.g., WO-2026-029-FAN-PORTAL.md
        search_pattern = os.path.join(TICKETS_DIR, f"*{ticket_num}*")
        matching_files = glob.glob(search_pattern)
        
        for filepath in matching_files:
            dest_path = os.path.join(ARCHIVE_DIR, os.path.basename(filepath))
            print(f"📦 Archiving: {os.path.basename(filepath)} ──► executed/")
            shutil.move(filepath, dest_path)
            archived_count += 1
            
    print(f"✅ Successfully archived {archived_count} files to executed/.")

if __name__ == "__main__":
    archive_resolved_tickets()
