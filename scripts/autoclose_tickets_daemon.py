"""
Sovereign OS — 48-Hour SDLC Ticket Auto-Close Daemon
Closes any ticket in RESOLVED state (state=4) that has not been updated in >= 48 hours.
Transitions state from 4 (RESOLVED) to 5 (CLOSED) and appends an automated system journal note.
"""
import os
import sys
import time
import sqlite3
import argparse
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
if not os.path.exists(DB_PATH) and os.path.exists("y:/dna/sovereign_now.db"):
    DB_PATH = "y:/dna/sovereign_now.db"

def run_autoclose_sweep(db_path=DB_PATH, force_all=False):
    now_iso = datetime.now().isoformat()
    conn = sqlite3.connect(db_path, timeout=30)
    cursor = conn.cursor()
    
    # Identify candidates: state = 4 (RESOLVED)
    if force_all:
        query = """
            SELECT number, short_description, sys_created_on, sys_updated_on, work_notes
            FROM sovereign_tickets
            WHERE state = 4
        """
    else:
        query = """
            SELECT number, short_description, sys_created_on, sys_updated_on, work_notes
            FROM sovereign_tickets
            WHERE state = 4
            AND (
                julianday('now') - julianday(COALESCE(sys_updated_on, sys_created_on)) >= 2.0
                OR sys_updated_on IS NULL
            )
        """
    cursor.execute(query)
    candidates = cursor.fetchall()
    
    if not candidates:
        print(f"[{now_iso}] [AUTOCLOSE] No tickets eligible for auto-close (0 candidates).")
        conn.close()
        return 0
        
    print(f"[{now_iso}] [AUTOCLOSE] Found {len(candidates)} tickets eligible for auto-close (force_all={force_all}).")
    
    closed_count = 0
    for row in candidates:
        ticket_number = row[0]
        work_notes = row[4] or ""
        
        reason = "all resolved tickets closure sweep" if force_all else "48 hours in Resolved state"
        journal_entry = f"\n[System Journal - {now_iso} - autoclose_daemon]\nTicket automatically closed after {reason}."
        updated_notes = work_notes + journal_entry
        
        cursor.execute("""
            UPDATE sovereign_tickets
            SET state = 5,
                work_notes = ?,
                sys_updated_on = ?
            WHERE number = ? AND state = 4
        """, (updated_notes, now_iso, ticket_number))
        
        closed_count += cursor.rowcount

    conn.commit()
    conn.close()
    
    print(f"[{now_iso}] [AUTOCLOSE] Successfully closed {closed_count} tickets.")
    return closed_count

def daemon_loop(interval_seconds=3600):
    print(f"[AUTOCLOSE DAEMON] Starting continuous sweep loop (interval: {interval_seconds}s)...")
    while True:
        try:
            run_autoclose_sweep()
        except Exception as e:
            print(f"[AUTOCLOSE DAEMON ERROR] {e}", file=sys.stderr)
        time.sleep(interval_seconds)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sovereign OS Ticket Auto-Close Utility")
    parser.add_argument("--once", action="store_true", help="Run once and exit immediately")
    parser.add_argument("--all", "--force", action="store_true", help="Close ALL resolved tickets immediately regardless of 48h age")
    parser.add_argument("--interval", type=int, default=3600, help="Daemon sweep interval in seconds (default: 3600)")
    args = parser.parse_args()
    
    if args.once or args.all:
        run_autoclose_sweep(force_all=args.all)
    else:
        daemon_loop(args.interval)

