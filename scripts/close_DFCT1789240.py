#!/usr/bin/env python3
import sqlite3
import os
import uuid
import urllib.request
import urllib.error
import json
import sys

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
walkthrough_path = '/home/james/sovereign_inbox/walkthroughs/walkthrough_DFCT1789240.md'
ticket_number = 'DFCT1789240'

print("Starting SDLC Closure Protocol for DFCT1789240...")

work_note = (
    "[Agent Journal - 2026-06-27T19:49:00Z - Antigravity]\n"
    "1. Optimized handle_context_injection in fanstack_chatbots.py to prevent persona regression and limit token burn rate via context budgets.\n"
    "2. Seeded today's NYM-PHI game room (823609) with Mets/Phillies advocates and key guest personas.\n"
    "3. Registered 10 TMI Telemetry Triggers for key play events (exit velocity, run scoring, pitch speed) to drive webslinger actions.\n"
    "4. Verified schedule and stack integrity."
)

# Step 1: Direct Database Synchronization
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check what tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    target_table = 'sovereign_tickets' if 'sovereign_tickets' in tables else 'rm_story'
    print(f"Targeting ticket table: {target_table}")
    
    # Check if ticket already exists
    cursor.execute(f"SELECT sys_id FROM {target_table} WHERE number = ?", (ticket_number,))
    ticket_row = cursor.fetchone()
    
    sys_id = ticket_row[0] if ticket_row else str(uuid.uuid4())
    
    if not ticket_row:
        print(f"Ticket {ticket_number} not found in DB. Creating...")
        cursor.execute(f"PRAGMA table_info({target_table})")
        cols = [c[1] for c in cursor.fetchall()]
        
        insert_cols = ['sys_id', 'number', 'short_description', 'description', 'state', 'priority', 'assigned_to', 'cmdb_ci']
        insert_vals = [
            sys_id,
            ticket_number,
            "Optimize Live Context Prompt Injection and Prevent Persona Regression",
            "Optimize context budget and prompt layout inside fanstack_chatbots.py to prevent persona regression and high token burn.",
            4, # Resolved
            3, # Medium
            "Antigravity",
            "fanstack"
        ]
        if 'type' in cols:
            insert_cols.append('type')
            insert_vals.append('DFCT')
            
        placeholders = ', '.join(['?'] * len(insert_cols))
        cols_str = ', '.join(insert_cols)
        cursor.execute(f"INSERT INTO {target_table} ({cols_str}) VALUES ({placeholders})", insert_vals)
    else:
        print(f"Ticket {ticket_number} found. Updating state to 4 (RESOLVED)...")
        cursor.execute(f"UPDATE {target_table} SET state = 4, sys_updated_on = CURRENT_TIMESTAMP WHERE number = ?", (ticket_number,))
        
    # Append work notes
    try:
        cursor.execute(f"SELECT work_notes FROM {target_table} WHERE number = ?", (ticket_number,))
        current_notes = cursor.fetchone()[0] or ""
        new_notes = current_notes + "\n\n" + work_note if current_notes else work_note
        cursor.execute(f"UPDATE {target_table} SET work_notes = ? WHERE number = ?", (new_notes, ticket_number))
        print("Updated database work notes.")
    except Exception as e:
        print(f"Could not update work notes: {e}")
        
    # Add attachment record
    if 'sys_attachment' in tables:
        attachment_sys_id = str(uuid.uuid4())
        file_name = os.path.basename(walkthrough_path)
        
        cursor.execute("SELECT sys_id FROM sys_attachment WHERE table_name = ? AND table_sys_id = ? AND file_name = ?",
                       (target_table, ticket_number, file_name))
        att_row = cursor.fetchone()
        
        if not att_row:
            cursor.execute("""
                INSERT INTO sys_attachment (sys_id, table_name, table_sys_id, file_name, content_type, file_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (attachment_sys_id, target_table, ticket_number, file_name, 'text/markdown', walkthrough_path))
            print("Registered attachment in sys_attachment.")
        else:
            # Update path
            cursor.execute("UPDATE sys_attachment SET file_path = ? WHERE table_sys_id = ? AND file_name = ?",
                           (walkthrough_path, ticket_number, file_name))
            print("Updated attachment path in sys_attachment.")
            
    conn.commit()
    conn.close()
    print("Database sync completed.")
except Exception as e:
    print(f"Database sync failed: {e}", file=sys.stderr)

# Step 2: Attempt REST API Calls to the SDLC Portal (Port 8095)
print("Attempting REST API calls to SDLC Portal on port 8095...")
try:
    url = f"http://127.0.0.1:8095/api/tickets/{ticket_number}"
    data = {
        "status": "RESOLVED",
        "work_notes": work_note
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        print(f"API PUT Response: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"API PUT request failed: {e}")

try:
    url = f"http://127.0.0.1:8095/api/tickets/{ticket_number}/attachments"
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    with open(walkthrough_path, 'rb') as f:
        file_content = f.read()
    filename = os.path.basename(walkthrough_path)
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
        print(f"API Attachment POST Response: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"API Attachment POST request failed: {e}")

print("SDLC Closure Protocol finished.")
