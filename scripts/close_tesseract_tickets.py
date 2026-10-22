#!/usr/bin/env python3
import sqlite3
import os
import uuid
import urllib.request
import urllib.error
import json
import sys
import subprocess

db_path = '/home/james/stacklabs/dna/sovereign_now.db'

tickets = [
    {
        "number": "STRY-0627-4D-CARD-STAGING",
        "walkthrough": "/home/james/sovereign_inbox/walkthroughs/walkthrough_STRY-0627-4D-CARD-STAGING.md",
        "work_notes": "[Agent Journal - 2026-07-13 - Antigravity]\n1. Decoupled 4D Baseball Card from HoloDex carousel, promoted to standalone room='tesseract_stage'.\n2. Replaced legacy 3D card layout with TesseractCardCanvas, implementing dynamic fabric normal mapping (wool, flannel, double-knit, performance) and era-based material morphing.\n3. Registered advocate assets (barf.png, barf-1970.png) in sys_media_asset and cmdb_ci_media_asset database tables.\n4. Verified clean Next.js build compilation and Tailscale cross-origin accessibility."
    },
    {
        "number": "DFCT1789244",
        "walkthrough": "/home/james/sovereign_inbox/walkthroughs/walkthrough_DFCT1789244.md",
        "work_notes": "[Agent Journal - 2026-07-13 - Antigravity]\n1. Patched Next.js CORS and frame-ancestors headers to authorize embedding in the Sovereign Portal cockpit iframe.\n2. Bound dev server port explicitly to 3026 to ensure proper Tailscale SSL reverse proxy mapping.\n3. Verified layout, touch-interactions, and uniform-switching in the standalone tesseract_stage."
    }
]

print("Starting SDLC Closure Protocol for Tesseract tickets...")

for t in tickets:
    ticket_number = t["number"]
    walkthrough_path = t["walkthrough"]
    work_note = t["work_notes"]
    
    print(f"\nProcessing Ticket: {ticket_number}")
    
    # Step 1: Direct Database Synchronization
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        target_table = 'sovereign_tickets' if 'sovereign_tickets' in tables else 'rm_story'
        
        # Check if ticket already exists
        cursor.execute(f"SELECT sys_id FROM {target_table} WHERE number = ?", (ticket_number,))
        ticket_row = cursor.fetchone()
        
        if ticket_row:
            print(f"Ticket {ticket_number} found in {target_table}. Updating state to 4 (RESOLVED)...")
            cursor.execute(f"UPDATE {target_table} SET state = 4, sys_updated_on = CURRENT_TIMESTAMP WHERE number = ?", (ticket_number,))
            
            # Append work notes
            cursor.execute(f"SELECT work_notes FROM {target_table} WHERE number = ?", (ticket_number,))
            current_notes = cursor.fetchone()[0] or ""
            new_notes = current_notes + "\n\n" + work_note if current_notes else work_note
            cursor.execute(f"UPDATE {target_table} SET work_notes = ? WHERE number = ?", (new_notes, ticket_number))
            print("Updated database ticket state & work notes.")
            
        # Add attachment record
        if 'sys_attachment' in tables and os.path.exists(walkthrough_path):
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
                cursor.execute("UPDATE sys_attachment SET file_path = ? WHERE table_sys_id = ? AND file_name = ?",
                               (walkthrough_path, ticket_number, file_name))
                print("Updated attachment path in sys_attachment.")
                
        conn.commit()
        conn.close()
        print("Database synchronization completed.")
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
        
    if os.path.exists(walkthrough_path):
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

# Step 3: Trigger cloud sync to Google Drive
print("\n🔄 Triggering targeted cloud synchronization to Google Drive...")
try:
    res = subprocess.run(["/home/james/stacklabs/scripts/sync_to_gdrive.sh"], capture_output=True, text=True)
    if res.returncode == 0:
        print("🟢 Cloud synchronization completed successfully.")
    else:
        print(f"⚠️ Cloud synchronization exited with status code {res.returncode}")
        print(res.stderr)
except Exception as e:
    print(f"❌ Failed to run sync_to_gdrive.sh: {e}")

print("\nSDLC Closure Protocol finished.")
