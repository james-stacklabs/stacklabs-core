#!/usr/bin/env python3
"""
Sovereign OS Vertex UAT Agent
Standalone daemon to automate Quality Assurance and UAT validation.
"""

import os
import sys
import time
import sqlite3
import urllib.request
from datetime import datetime

# Path definitions
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"

# Port mapping based on ticket metadata (cmdb_ci, description, or title)
PORT_MAPPING = {
    "SAMTRACKER": 3004,
    "SAMTRACKER 2.0": 3004,
    "FANSTACK": 3009,
    "AETHER VET": 3015,
    "GARDENSTACK": 3016,
    "SPORTS": 3010,
    "SOVEREIGN SPORTS": 3010,
    "PGA": 3010
}

def authenticate_gcp():
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"[Vertex UAT] GCP Credentials not found at {CREDENTIALS_PATH}. Proceeding with mock auth.")
        return False
    try:
        # Standard Vertex AI authentication using GCP Credentials path
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
        import google.auth
        credentials, project = google.auth.default()
        print(f"[Vertex UAT] GCP Authenticated successfully for project: {project}")
        return True
    except Exception as e:
        print(f"[Vertex UAT] GCP Authentication failed: {e}")
        return False

def query_target_port(conn, ticket_id, cmdb_ci, description, title):
    # Match against PORT_MAPPING using case-insensitive check
    text_to_search = f"{cmdb_ci} {description} {title}".upper()
    for key, port in PORT_MAPPING.items():
        if key in text_to_search:
            print(f"[Vertex UAT] Identified port {port} for node: {key}")
            return port
    # Default fallback to GardenStack port 3016 or SamTracker 3004
    print(f"[Vertex UAT] No matching node found. Defaulting to SamTracker (Port 3004).")
    return 3004

def perform_endpoint_validation(port):
    import ssl
    urls = [f"http://localhost:{port}/", f"https://localhost:{port}/"]
    for url in urls:
        print(f"[Vertex UAT] Testing endpoint URL: {url}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Vertex-UAT-Agent/1.0'})
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                status_code = response.getcode()
                if status_code == 200:
                    print(f"[Vertex UAT] Endpoint verification SUCCESS (Code 200 OK) for {url}")
                    return True
        except Exception as e:
            print(f"[Vertex UAT] Endpoint verification FAILED for {url} with error: {e}")
    return False

def process_uat_ticket(ticket):
    sys_id, number, title, description, cmdb_ci = ticket
    print(f"\n[Vertex UAT] 🧪 Processing UAT for ticket: {number} — {title}")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Read the walkthrough path from the 'sys_attachment' table
    cur.execute("""
        SELECT file_path, file_name FROM sys_attachment 
        WHERE table_sys_id = ? OR table_sys_id = ? 
        ORDER BY sys_created_on DESC LIMIT 1
    """, (sys_id, number))
    attachment_row = cur.fetchone()
    
    if not attachment_row:
        print(f"[Vertex UAT ⚠️] No walkthrough attachment found for ticket {number}. Skipping.")
        conn.close()
        return
        
    walkthrough_path, file_name = attachment_row
    print(f"[Vertex UAT] Found Walkthrough file: {walkthrough_path}")
    
    # 2. Identify the target port and run endpoint validation check
    port = query_target_port(conn, number, cmdb_ci, description, title)
    validation_success = perform_endpoint_validation(port)
    
    if not validation_success:
        print(f"[Vertex UAT ❌] UAT validation failed for ticket {number} on Port {port}.")
        # Re-assign or log failure in work notes
        failure_note = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Vertex UAT automated validation FAILED on Port {port}. Please verify the server status."
        cur.execute("UPDATE sovereign_tickets SET work_notes = work_notes || ? WHERE sys_id = ?", (failure_note, sys_id))
        conn.commit()
        conn.close()
        return
        
    # 3. Append signed UAT timestamp log to the walkthrough file
    if os.path.exists(walkthrough_path):
        try:
            timestamp_entry = f"\n\n## 🧪 VERTEX UAT VERIFICATION SIGN-OFF\n- **Status:** APPROVED\n- **Timestamp:** {datetime.now().isoformat()}\n- **Agent:** Vertex_UAT_Agent\n- **Validation Check:** Port {port} responded with HTTP 200 OK\n"
            with open(walkthrough_path, "a") as f:
                f.write(timestamp_entry)
            print(f"[Vertex UAT] Signed and appended timestamp log to: {walkthrough_path}")
        except Exception as e:
            print(f"[Vertex UAT] Error writing to walkthrough file: {e}")
    else:
        print(f"[Vertex UAT ⚠️] Walkthrough physical file not found at {walkthrough_path} to append sign-off.")

    # 4. Set state to 3 ('RESOLVED' / 'DONE')
    success_note = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Vertex UAT automated validation SUCCESS on Port {port}. Walkthrough file signed. Ticket marked RESOLVED."
    cur.execute("""
        UPDATE sovereign_tickets
        SET state = 3, assigned_to = 'james', work_notes = work_notes || ?, sys_updated_on = ?
        WHERE sys_id = ?
    """, (success_note, datetime.now().isoformat(), sys_id))
    
    conn.commit()
    conn.close()
    
    print(f"[Vertex UAT ✅] Ticket {number} successfully resolved!")

def run_daemon():
    print("=" * 60)
    print(" VERTEX AUTOMATED UAT VALIDATION AGENT INITIATED")
    print("=" * 60)
    
    authenticate_gcp()
    
    print(f"[Vertex UAT] Scanning database: {DB_PATH}")
    
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            # Fetch tickets assigned to Vertex_UAT_Agent in state 'Testing'
            cur.execute("""
                SELECT sys_id, number, short_description, description, cmdb_ci 
                FROM sovereign_tickets 
                WHERE assigned_to = 'Vertex_UAT_Agent' AND state = 'Testing'
            """)
            tickets = cur.fetchall()
            conn.close()
            
            if tickets:
                for ticket in tickets:
                    process_uat_ticket(ticket)
            else:
                print("[Vertex UAT] 💤 Waiting for tickets in state 'Testing'...", end='\r')
                
        except Exception as e:
            print(f"[Vertex UAT Error] Loop error: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    # Check if a single-run validation is requested via args
    if len(sys.argv) > 1 and sys.argv[1] == "--single-run":
        authenticate_gcp()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT sys_id, number, short_description, description, cmdb_ci 
            FROM sovereign_tickets 
            WHERE assigned_to = 'Vertex_UAT_Agent' AND state = 'Testing'
        """)
        tickets = cur.fetchall()
        conn.close()
        for ticket in tickets:
            process_uat_ticket(ticket)
        sys.exit(0)
        
    run_daemon()
