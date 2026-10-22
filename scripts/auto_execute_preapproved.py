#!/usr/bin/env python3
import os
import re
import sys
import sqlite3
import datetime
import shutil
import argparse
import paramiko

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
INBOX_DIR = "/home/james/sovereign_inbox"
INGRESS_DIR = "/var/tickets/ingress"

def find_payload_file(ticket_id, description):
    # 1. Try to extract filename from description
    # Format from execute_staged_orders: "- File Name: {filename}"
    filename_match = re.search(r"-\s*File\s*Name:\s*(.*)", description, re.IGNORECASE)
    if filename_match:
        fname = filename_match.group(1).strip()
        # Search for this file in INBOX_DIR recursively
        for root, dirs, files in os.walk(INBOX_DIR):
            if fname in files:
                return os.path.join(root, fname)

    # Extract base identifier (e.g. 2026-0713-AUTOEXEC from WO-2026-0713-AUTOEXEC)
    base_id = ticket_id
    dash_index = ticket_id.find('-')
    if dash_index != -1:
        base_id = ticket_id[dash_index+1:]

    # 2. Fallback: Search for any file in INBOX_DIR containing base_id in its name
    base_id_lower = base_id.lower()
    for root, dirs, files in os.walk(INBOX_DIR):
        for f in files:
            if base_id_lower in f.lower():
                # Avoid files that are walkthroughs
                if "walkthrough" in f.lower():
                    continue
                return os.path.join(root, f)
                
    return None


def execute_on_argo(ticket_id):
    print(f"  [ArgoSSH] Connecting to argo.taila01894.ts.net via SSH...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect("argo.taila01894.ts.net", username="james")
        # Invoke agy run [ticket_id] headlessly
        cmd = f"agy run {ticket_id}"
        print(f"  [ArgoSSH] Running command: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Read outputs
        out_content = stdout.read().decode("utf-8", errors="ignore")
        err_content = stderr.read().decode("utf-8", errors="ignore")
        
        # Check exit status
        exit_status = stdout.channel.recv_exit_status()
        
        return {
            "status": "success" if exit_status == 0 else "error",
            "exit_code": exit_status,
            "output": out_content,
            "errors": err_content
        }
    except Exception as e:
        return {
            "status": "error",
            "exit_code": -1,
            "message": str(e),
            "output": "",
            "errors": str(e)
        }
    finally:
        ssh.close()

def main():
    parser = argparse.ArgumentParser(description="Sovereign Auto-Executor Daemon")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry-run check without remote execution")
    args = parser.parse_args()

    print(f"[{datetime.datetime.now()}] Starting auto_execute_preapproved.py...")
    if args.dry_run:
        print("🔧 RUNNING IN DRY-RUN MODE")

    if not os.path.exists(INGRESS_DIR):
        os.makedirs(INGRESS_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query for preapproved or approved_to_run tickets in state 1 (OPEN/STAGED)
    cursor.execute("""
        SELECT sys_id, number, short_description, description, state, priority, assigned_to
        FROM sovereign_tickets
        WHERE state = 1 AND (approved_to_run = 1 OR preapproved = 1)
    """)
    tickets = cursor.fetchall()
    
    if not tickets:
        print("💤 No preapproved or approved_to_run tickets found in state 1.")
        conn.close()
        return

    print(f"🎫 Found {len(tickets)} candidate tickets for execution.")
    
    for row in tickets:
        sys_id, ticket_id, short_desc, description, state, priority, assigned_to = row
        print(f"\n[PROCESSING] {ticket_id} - {short_desc}")
        
        # 1. File Staging: Locate payload and copy/move to /var/tickets/ingress/
        payload_path = find_payload_file(ticket_id, description or "")
        dest_payload_path = None
        
        if payload_path:
            filename = os.path.basename(payload_path)
            dest_payload_path = os.path.join(INGRESS_DIR, filename)
            try:
                shutil.copy2(payload_path, dest_payload_path)
                print(f"  [STAGING] Copied payload: {filename} -> {INGRESS_DIR}")
            except Exception as e:
                print(f"  [ERROR] Failed to stage payload file: {e}")
        else:
            print(f"  [WARNING] No payload file found in inbox for ticket {ticket_id}.")
            # Write a placeholder payload to ingress
            dest_payload_path = os.path.join(INGRESS_DIR, f"{ticket_id}_payload.md")
            try:
                with open(dest_payload_path, "w") as f:
                    f.write(f"# Auto-Generated Payload for {ticket_id}\n\nShort Description: {short_desc}\n")
                print(f"  [STAGING] Created placeholder payload in {dest_payload_path}")
            except Exception as e:
                print(f"  [ERROR] Failed to write placeholder payload: {e}")

        # Naming convention for execution log: /var/tickets/ingress/{ticket_id}_execution.log
        log_path = os.path.join(INGRESS_DIR, f"{ticket_id}_execution.log")
        
        # 2. Execution Phase
        success = False
        execution_output = ""
        execution_errors = ""
        
        if args.dry_run:
            print(f"  [DRY-RUN] Simulating headless execution of {ticket_id}...")
            execution_output = f"Dry-run execution simulated successfully for ticket {ticket_id}.\nShort Description: {short_desc}"
            success = True
            
            # Write simulation log
            with open(log_path, "w") as lf:
                lf.write(f"=== DRY-RUN EXECUTION LOG FOR {ticket_id} ===\n")
                lf.write(f"Timestamp: {datetime.datetime.now()}\n")
                lf.write(f"Payload Staged: {dest_payload_path}\n")
                lf.write(f"Simulation Status: SUCCESS\n")
        else:
            print(f"  [EXECUTION] Triggering remote execution of {ticket_id}...")
            res = execute_on_argo(ticket_id)
            
            execution_output = res.get("output", "")
            execution_errors = res.get("errors", "")
            
            # Write to execution log
            with open(log_path, "w") as lf:
                lf.write(f"=== REMOTE EXECUTION LOG FOR {ticket_id} ===\n")
                lf.write(f"Timestamp: {datetime.datetime.now()}\n")
                lf.write(f"Payload Staged: {dest_payload_path}\n")
                lf.write(f"Exit Code: {res.get('exit_code')}\n\n")
                lf.write("--- STDOUT ---\n")
                lf.write(execution_output)
                lf.write("\n--- STDERR ---\n")
                lf.write(execution_errors)
            
            if res.get("status") == "success":
                success = True
                print("  [✔] Remote execution succeeded.")
            else:
                success = False
                print(f"  [❌] Remote execution failed: {res.get('errors')}")

        # 3. State Management & Database Loopback
        now_str = datetime.datetime.now().isoformat()
        if success:
            status_note = f"Auto-execution succeeded.\nLog file: {log_path}"
            cursor.execute("""
                UPDATE sovereign_tickets 
                SET state = 4, work_notes = ?, sys_updated_on = ? 
                WHERE number = ?
            """, (status_note, now_str, ticket_id))
            cursor.execute("""
                UPDATE sys_sdlc_task 
                SET state = 'RESOLVED', sys_updated_on = ? 
                WHERE task_id = ?
            """, (now_str, ticket_id))
            print(f"  [DATABASE] Ticket {ticket_id} state updated to RESOLVED (4).")
        else:
            error_note = f"Auto-execution failed.\nErrors: {execution_errors[:200]}\nLog file: {log_path}"
            cursor.execute("""
                UPDATE sovereign_tickets 
                SET work_notes = ?, sys_updated_on = ? 
                WHERE number = ?
            """, (error_note, now_str, ticket_id))
            cursor.execute("""
                UPDATE sys_sdlc_task 
                SET state = 'STAGED', sys_updated_on = ? 
                WHERE task_id = ?
            """, (now_str, ticket_id))
            print(f"  [DATABASE] Ticket {ticket_id} failed. Database logged error details.")

    conn.commit()
    conn.close()
    print(f"[{datetime.datetime.now()}] Auto-execution sweep complete.")

if __name__ == "__main__":
    main()
