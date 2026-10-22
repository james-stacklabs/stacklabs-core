import time
import os
import subprocess

POLL_INTERVAL = 60 # Check operations every minute

def execute_discovery():
    script_path = "/home/james/stacklabs/08_CMDB_Discovery/cmdb_discovery.py"
    if os.path.exists(script_path):
        print("\n=== [VESPER] Triggering Autonomous Discovery Sweep ===")
        subprocess.run(["python3", script_path])

def execute_smuggler_bay():
    print("\n=== [VESPER] Engaging Rclone Smuggler Bay Pipeline ===")
    dropzone_target = "/home/james/stacklabs/dna/archives/smuggler_dropzone/"
    
    try:
        # Move files from the cloud Dropzone to local SSD, instantly deleting the cloud copies
        subprocess.run(["rclone", "move", "sovereign_os:Sovereign_Dropzone", dropzone_target, "-v", "--ignore-existing"], check=True)
    except Exception as e:
        print(f"[VESPER ERROR] Smuggler Bay Sync Failed: {str(e)}")

def execute_greenstack():
    script_path = "/home/james/stacklabs/03_Ultron_Integration/greenstack_sync.py"
    if os.path.exists(script_path):
        print("\n=== [VESPER] Triggering GreenStack Synchronicity ===")
        subprocess.run(["python3", script_path])

def execute_investor_followups():
    print("\n=== [VESPER] Auditing Investor Hold Cadence ===")
    db_path = "/home/james/stacklabs/dna/sovereign_now.db"
    if not os.path.exists(db_path):
        print(f"[VESPER ERROR] Database not found at {db_path}")
        return
        
    try:
        import sqlite3
        from datetime import datetime
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        tickets = conn.execute("""
            SELECT number, sys_created_on, state, short_description 
            FROM sovereign_tickets 
            WHERE number IN ('WO-2026-005-PAUL-PING', 'STRY-06092026-WILDSEED-PIVOT')
        """).fetchall()
        
        for ticket in tickets:
            num = ticket['number']
            created_str = ticket['sys_created_on']
            state = ticket['state']
            
            if state in (4, 5):
                print(f"[VESPER] Ticket {num} is resolved/closed. Skipping follow-up audit.")
                continue
                
            try:
                if "T" in created_str:
                    created_dt = datetime.fromisoformat(created_str.split(".")[0].replace("Z", ""))
                else:
                    created_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
            except Exception as parse_err:
                print(f"[VESPER ERROR] Could not parse date '{created_str}' for {num}: {str(parse_err)}")
                continue
                
            elapsed = datetime.now() - created_dt
            days_elapsed = elapsed.days
            
            print(f"[VESPER] Ticket {num} - Staged follow-up hold. Days elapsed: {days_elapsed}/3.")
            if days_elapsed >= 3:
                print(f"[VESPER WARNING] Follow-up triggered for {num}! 3-day hold window has expired.")
                
        conn.close()
    except Exception as e:
        print(f"[VESPER ERROR] Investor Follow-up Check Failed: {str(e)}")

def execute_ticket_autoclose():
    print("\n=== [VESPER] Executing 48-Hour Ticket Auto-Closure Escalation Sweep ===")
    db_path = "/home/james/stacklabs/dna/sovereign_now.db"
    if not os.path.exists(db_path):
        print(f"[VESPER ERROR] Database not found at {db_path}")
        return
        
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Identify tickets to close: state = 4 (RESOLVED), older than 48 hours (2 days)
        c.execute("""
            SELECT sys_id, number 
            FROM sovereign_tickets 
            WHERE state = 4 AND sys_updated_on < datetime('now', '-2 days')
        """)
        to_close = c.fetchall()
        
        if to_close:
            for sys_id, number in to_close:
                print(f"[VESPER] Auto-closing resolved ticket {number} (sys_id: {sys_id})")
                c.execute("""
                    UPDATE sovereign_tickets 
                    SET state = 5, work_notes = 'Automated 48-hour auto-closure escalation sweep.', sys_updated_on = CURRENT_TIMESTAMP
                    WHERE sys_id = ?
                """, (sys_id,))
                
                c.execute("""
                    UPDATE sys_sdlc_task 
                    SET state = 'CLOSED' 
                    WHERE task_id = ?
                """, (number,))
            
            conn.commit()
            print(f"✅ Successfully closed {len(to_close)} tickets.")
        else:
            print("[VESPER] No resolved tickets eligible for 48-hour auto-closure.")
            
        conn.close()
    except Exception as e:
        print(f"[VESPER ERROR] Ticket Auto-Closure Failed: {str(e)}")

if __name__ == "__main__":
    print("[VESPER KERNEL] Initializing Core Scheduler Loop...")
    cycles = 0
    while True:
        cycles += 1
        print(f"\n[VESPER KERNEL] Cycle #{cycles} commencing...")
        execute_greenstack()
        execute_smuggler_bay()
        execute_investor_followups()
        execute_ticket_autoclose()
        
        # Perform discovery sweep every 5 minutes (5 cycles)
        if cycles % 5 == 1:
            execute_discovery()
            
        time.sleep(POLL_INTERVAL)

