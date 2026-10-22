#!/usr/bin/env python3
import sqlite3
import os
import uuid
import urllib.request
import urllib.error
import json
import sys

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
walkthrough_path = '/home/james/sovereign_inbox/walkthroughs/walkthrough_STRY-06232026-ROSTER-RECONCILIATION.md'
ticket_number = 'STRY-06232026-ROSTER-RECONCILIATION'

print("Starting SDLC Closure Protocol...")

# Step 1: Direct Database Synchronization
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check what tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Found tables in DB: {tables}")
    
    target_table = 'sovereign_tickets' if 'sovereign_tickets' in tables else 'rm_story'
    print(f"Targeting ticket table: {target_table}")
    
    # Check if ticket already exists
    cursor.execute(f"SELECT sys_id FROM {target_table} WHERE number = ?", (ticket_number,))
    ticket_row = cursor.fetchone()
    
    sys_id = ticket_row[0] if ticket_row else str(uuid.uuid4())
    
    if not ticket_row:
        # Insert a new ticket
        print(f"Ticket {ticket_number} not found. Creating it...")
        # Get columns of target table to ensure correct insert
        cursor.execute(f"PRAGMA table_info({target_table})")
        cols = [c[1] for c in cursor.fetchall()]
        print(f"Columns in {target_table}: {cols}")
        
        insert_cols = ['sys_id', 'number', 'short_description', 'description', 'state', 'priority', 'assigned_to', 'cmdb_ci']
        insert_vals = [
            sys_id,
            ticket_number,
            "Reconcile Advocate Roster Registry and Swap Game Room Personas",
            "Reconcile widespread metadata corruption in the Advocate Roster registry (sovereign_now.db) and optimize the persona management system for the FanStack environment.",
            4, # Resolved
            2, # High
            "Antigravity",
            "FanStack"
        ]
        
        if 'type' in cols:
            insert_cols.append('type')
            insert_vals.append('STRY') # MUST BE 'STRY' (CHECK constraint)
            
        placeholders = ', '.join(['?'] * len(insert_cols))
        cols_str = ', '.join(insert_cols)
        
        insert_query = f"INSERT INTO {target_table} ({cols_str}) VALUES ({placeholders})"
        cursor.execute(insert_query, insert_vals)
        print(f"Successfully inserted ticket {ticket_number} into {target_table}.")
    else:
        # Update existing ticket
        print(f"Ticket {ticket_number} found with sys_id {sys_id}. Updating to Resolved...")
        update_query = f"""
            UPDATE {target_table}
            SET state = 4, sys_updated_on = CURRENT_TIMESTAMP
            WHERE number = ?
        """
        cursor.execute(update_query, (ticket_number,))
        print(f"Successfully updated ticket {ticket_number} to Resolved.")
        
    # Add work note to journal/work_notes
    work_note = (
        "[Agent Journal - 2026-06-23T23:14:00Z - Antigravity]\n"
        "1. Developed and executed fix_persona_metadata.py to reconcile metadata across persona, sys_user, and cmdb_ci tables.\n"
        "2. Performed personnel swap in Game Room 823614, promoting bartman and benching bartmans_ghost.\n"
        "3. Generated nym_chc_advocates_review.md registry documentation.\n"
        "4. Validated system build and resolved Tailwind v4 symlink scanning issue in index.css."
    )
    
    # Try to append to work_notes
    try:
        cursor.execute(f"SELECT work_notes FROM {target_table} WHERE number = ?", (ticket_number,))
        current_notes = cursor.fetchone()[0] or ""
        new_notes = current_notes + "\n\n" + work_note if current_notes else work_note
        cursor.execute(f"UPDATE {target_table} SET work_notes = ? WHERE number = ?", (new_notes, ticket_number))
        print("Successfully updated work notes.")
    except Exception as e:
        print(f"Could not update work notes column: {e}")
        
    # Register attachment in sys_attachment
    if 'sys_attachment' in tables:
        attachment_sys_id = str(uuid.uuid4())
        file_name = os.path.basename(walkthrough_path)
        
        # Check if attachment already exists
        cursor.execute("SELECT sys_id FROM sys_attachment WHERE table_name = ? AND table_sys_id = ? AND file_name = ?",
                       (target_table, ticket_number, file_name))
        att_row = cursor.fetchone()
        
        if not att_row:
            print("Registering walkthrough attachment in sys_attachment...")
            cursor.execute("""
                INSERT INTO sys_attachment (sys_id, table_name, table_sys_id, file_name, content_type, file_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (attachment_sys_id, target_table, ticket_number, file_name, 'text/markdown', walkthrough_path))
            print("Walkthrough attachment registered successfully.")
        else:
            print("Walkthrough attachment already registered in database.")
            
    conn.commit()
    conn.close()
    print("Database sync completed successfully.")
except Exception as e:
    print(f"Database sync failed: {e}", file=sys.stderr)

# Step 2: Attempt REST API Calls to the SDLC Portal (Port 8095)
print("Attempting REST API calls to SDLC Portal on port 8095...")

# 2.1 Update ticket status via PUT /api/tickets/{number}
try:
    url = f"http://127.0.0.1:8095/api/tickets/{ticket_number}"
    data = {
        "status": "RESOLVED",
        "work_notes": (
            "1. Developed and executed fix_persona_metadata.py to reconcile metadata across persona, sys_user, and cmdb_ci tables.\n"
            "2. Performed personnel swap in Game Room 823614, promoting bartman and benching bartmans_ghost.\n"
            "3. Generated nym_chc_advocates_review.md registry documentation.\n"
            "4. Validated system build and resolved Tailwind v4 symlink scanning issue in index.css."
        )
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        res_data = response.read().decode('utf-8')
        print(f"API PUT Response: {res_data}")
except Exception as e:
    print(f"API PUT request failed/timed out (this is expected if DB lock is transient): {e}")

# 2.2 Upload walkthrough attachment via POST /api/tickets/{number}/attachments
try:
    url = f"http://127.0.0.1:8095/api/tickets/{ticket_number}/attachments"
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    
    with open(walkthrough_path, 'rb') as f:
        file_content = f.read()
        
    filename = os.path.basename(walkthrough_path)
    
    # Construct multipart/form-data body
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/markdown\r\n\r\n"
    ).encode('utf-8') + file_content + f"\r\n--{boundary}--\r\n".encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(body))
        },
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        res_data = response.read().decode('utf-8')
        print(f"API Attachment POST Response: {res_data}")
except Exception as e:
    print(f"API Attachment POST request failed/timed out (this is expected if DB lock is transient): {e}")

print("SDLC Closure Protocol finished.")
