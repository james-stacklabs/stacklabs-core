#!/usr/bin/env python3
import os
import re
import sqlite3
import uuid
import shutil
import paramiko

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
INBOX_TICKETS_DIR = "/home/james/sovereign_inbox/tickets"
INBOX_DIR = "/home/james/sovereign_inbox"

def execute_on_argo(work_order_id):
    print(f"  [ArgoSSH] Connecting to argo.taila01894.ts.net via SSH...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect("argo.taila01894.ts.net", username="james")
        print(f"  [ArgoSSH] Running: antigravity --run {work_order_id}")
        stdin, stdout, stderr = ssh.exec_command(f"antigravity --run {work_order_id}")
        output = stdout.read().decode("utf-8")
        errors = stderr.read().decode("utf-8")
        return {"status": "success", "output": output, "errors": errors}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        ssh.close()


def parse_work_order_file(filepath):
    filename = os.path.basename(filepath)
    print(f"Parsing file: {filename}")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    lines = [line.strip() for line in content.splitlines()]
    
    # Parse title (first line)
    title = ""
    if lines:
        first_line = lines[0]
        # Match e.g. "📡 ANTIGRAVITY WORK ORDER: SOVEREIGN OS WORK ORDER SYNC AUTOMATION"
        match = re.search(r"(?:ANTIGRAVITY\s+)?WORK\s+ORDER:\s*(.*)$", first_line, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
        else:
            # Fallback H1 search
            h1_match = re.search(r"^#\s*(.*)$", first_line)
            if h1_match:
                title = h1_match.group(1).strip()
            else:
                title = os.path.splitext(filename)[0]

    # Clean title from emojis/brackets
    title = re.sub(r'[\u2600-\u27BF]|[\u2000-\u3300]|[\uD83C-\uDBFF\uDC00-\uDFFF]', '', title).strip(" :.-–—")

    # Helper to find values in tabbed key-value lines
    ticket_id = ""
    priority = "3"
    assigned_to = "antigravity"
    
    for idx, line in enumerate(lines):
        if line.lower() == "ticket id":
            if idx + 1 < len(lines):
                ticket_id = lines[idx + 1].strip("` \t")
        elif line.lower() == "priority":
            if idx + 1 < len(lines):
                p_val = lines[idx + 1].strip()
                p_match = re.search(r"P(\d+)", p_val, re.IGNORECASE)
                if p_match:
                    priority = p_match.group(1)
        elif line.lower() in ["assigned to", "assigned_to"]:
            if idx + 1 < len(lines):
                assigned_to = lines[idx + 1].strip("` \t")

    # Fallbacks via regex if tab structure is different
    if not ticket_id:
        pattern_match = re.search(r'\b((?:STRY|INC|DFCT|ENHC|REQ|WO)-[A-Z0-9\-_]+)\b', content, re.IGNORECASE)
        if pattern_match:
            ticket_id = pattern_match.group(1).upper()

    if not ticket_id:
        id_match = re.search(r'\b(Ticket ID|Ticket|ID)\b\s*:?\s*`?([A-Z0-9\-_]+)`?', content, re.IGNORECASE)
        if id_match:
            val = id_match.group(2)
            val_upper = val.upper()
            if len(val) >= 4 and val_upper not in ["ENTIFIED", "GETS", "GING", "EO", "S", "EBAR", "ATION", "UAL"]:
                ticket_id = val
            
    if not ticket_id:
        # Generate deterministic md5 hash-based ID if none found
        import hashlib
        h = hashlib.md5(content.encode('utf-8', errors='ignore')).hexdigest()
        ticket_id = "INC" + str(int(h, 16) % 10000000)

    # Determine type
    tid_up = ticket_id.upper()
    if "REQ" in tid_up:
        ticket_type = "REQ"
    elif "DFCT" in tid_up:
        ticket_type = "DFCT"
    elif "ENHC" in tid_up:
        ticket_type = "ENHC"
    elif "INC" in tid_up:
        ticket_type = "INC"
    else:
        ticket_type = "STRY"

    return {
        "id": ticket_id,
        "type": ticket_type,
        "title": title,
        "priority": int(priority),
        "assigned_to": assigned_to,
        "content": content,
        "filename": filename
    }

def stage_ticket_in_db(ticket):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if ticket already exists by number
    cursor.execute("SELECT sys_id, state FROM sovereign_tickets WHERE number = ?", (ticket["id"],))
    row = cursor.fetchone()
    
    existing_sys_id = row[0] if row else None
    existing_state = row[1] if row else None

    # Check if a state/status is specified in content
    state_match = re.search(r'\b(State|Status)\s*:\s*`?([A-Za-z_ ]+)`?', ticket['content'], re.IGNORECASE)
    file_state = state_match.group(2).strip() if state_match else None

    if file_state:
        if file_state.lower() in ["wip", "work in progress", "open"]:
            num_state = 2
            sdlc_state = 'WIP'
        elif file_state.lower() in ["resolved", "closed", "complete"]:
            num_state = 4
            sdlc_state = 'RESOLVED'
        else:
            num_state = 1
            sdlc_state = 'STAGED'
    elif existing_state is not None:
        num_state = existing_state
        if num_state == 2:
            sdlc_state = 'WIP'
        elif num_state in [4, 5]:
            sdlc_state = 'RESOLVED'
        else:
            sdlc_state = 'STAGED'
    else:
        num_state = 1
        sdlc_state = 'STAGED'

    description_text = f"Google Drive Work Order Sync automatically pulled and staged this file.\n\n- File Name: {ticket['filename']}\n- Source: {INBOX_TICKETS_DIR}/{ticket['filename']}"

    # 1. Update/Insert into sovereign_tickets
    if row:
        sys_id = row[0]
        print(f"  [sovereign_tickets] Updating ticket {ticket['id']}...")
        cursor.execute("""
            UPDATE sovereign_tickets 
            SET type = ?, short_description = ?, description = ?, state = ?, priority = ?, assigned_to = ?, cmdb_ci = ?, work_notes = ?, sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (ticket["type"], ticket["title"], description_text, num_state, ticket["priority"], ticket["assigned_to"], 'GoogleDriveSync', 'File sync executed and staged.', sys_id))
    else:
        sys_id = uuid.uuid4().hex
        print(f"  [sovereign_tickets] Inserting new ticket {ticket['id']}...")
        cursor.execute("""
            INSERT INTO sovereign_tickets 
              (sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sys_id, ticket["id"], ticket["type"], ticket["title"], description_text, num_state, ticket["priority"], ticket["assigned_to"], 'GoogleDriveSync', 'File sync executed and staged.'))

    # 2. Update/Insert into sys_sdlc_task
    cursor.execute("SELECT task_id FROM sys_sdlc_task WHERE task_id = ?", (ticket["id"],))
    task_row = cursor.fetchone()
    
    task_type_db = ticket["type"].lower() if ticket["type"] == "STRY" else "story"
    if task_row:
        print(f"  [sys_sdlc_task] Updating task {ticket['id']}...")
        cursor.execute("""
            UPDATE sys_sdlc_task
            SET task_type = ?, state = ?, short_description = ?
            WHERE task_id = ?
        """, (task_type_db, sdlc_state, ticket["title"], ticket["id"]))
    else:
        print(f"  [sys_sdlc_task] Inserting new task {ticket['id']}...")
        cursor.execute("""
            INSERT INTO sys_sdlc_task (task_id, task_type, state, module_target, short_description)
            VALUES (?, ?, ?, ?, ?)
        """, (ticket["id"], task_type_db, sdlc_state, 'portal_core', ticket["title"]))

    conn.commit()
    conn.close()
    print(f"✅ Staged ticket {ticket['id']} successfully.")

def main():
    print("🚀 Running execute_staged_orders.py parser...")
    
    # Check both tickets folder and root inbox (just in case they are not yet organized)
    paths_to_scan = [INBOX_TICKETS_DIR, INBOX_DIR]
    scanned_files = []
    
    for scan_dir in paths_to_scan:
        if not os.path.exists(scan_dir):
            continue
        for entry in os.scandir(scan_dir):
            if entry.is_file() and entry.name.endswith(".md"):
                # Ignore walkthroughs by filename
                if "walkthrough" in entry.name.lower():
                    continue
                # Avoid duplicates
                if entry.name not in scanned_files:
                    # Filter for files that contain "ANTIGRAVITY WORK ORDER" or "WORK ORDER"
                    try:
                        with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                            first_few_lines = f.read(500)
                        # Skip if it is a walkthrough
                        if "walkthrough" in first_few_lines.lower():
                            continue
                        if "WORK ORDER" in first_few_lines.upper():
                            scanned_files.append((entry.name, entry.path))
                    except Exception:
                        pass
                        
    staged_count = 0
    executed_dir = os.path.join(INBOX_DIR, "executed")
    os.makedirs(executed_dir, exist_ok=True)
    for filename, filepath in scanned_files:
        try:
            ticket = parse_work_order_file(filepath)
            stage_ticket_in_db(ticket)
            
            # Check if this is an Emergency Change (Priority 1)
            if ticket["priority"] == 1:
                print(f"  [⚡] Emergency Change detected for ticket {ticket['id']}. Initiating SSH execution on Argo...")
                res = execute_on_argo(ticket["id"])
                
                # Update ticket state to RESOLVED (4) and save output in DB
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                if res.get("status") == "success":
                    status_note = f"Executed on Argo. Output: {res.get('output', '')[:500]}"
                    cursor.execute("UPDATE sovereign_tickets SET state = 4, work_notes = ?, sys_updated_on = CURRENT_TIMESTAMP WHERE number = ?", (status_note, ticket["id"]))
                    cursor.execute("UPDATE sys_sdlc_task SET state = 'RESOLVED' WHERE task_id = ?", (ticket["id"],))
                    print(f"  [✔] SSH execution succeeded.")
                else:
                    error_note = f"Argo SSH execution failed: {res.get('message', '')[:500]}"
                    cursor.execute("UPDATE sovereign_tickets SET state = 1, work_notes = ?, sys_updated_on = CURRENT_TIMESTAMP WHERE number = ?", (error_note, ticket["id"]))
                    cursor.execute("UPDATE sys_sdlc_task SET state = 'STAGED' WHERE task_id = ?", (ticket["id"],))
                    print(f"  [❌] SSH execution failed: {res.get('message')}")
                conn.commit()
                conn.close()
            else:
                print(f"  [i] Normal change staged. Remaining in STAGED/WIP state.")

            # Physically move the source file to executed/ to prevent duplicate processing
            dest_path = os.path.join(executed_dir, filename)
            shutil.move(filepath, dest_path)
            print(f"Moved ingested file: {filename} -> executed/")
            
            staged_count += 1
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            
    print(f"📊 Completed staging. Total staged work orders: {staged_count}")
    # Write count to stdout/file for backend API consumption if needed
    return staged_count

if __name__ == "__main__":
    main()
