#!/usr/bin/env python3
import os
import sys
import time
import shutil
import sqlite3
import datetime
import re
import firebase_admin
from firebase_admin import credentials, db

# Configuration
APIARY_ROOT = os.path.realpath("/home/james/stacklabs")
ALLOWED_PREFIXES = [APIARY_ROOT]  # Can be mapped to specific subdirs later
SERVICE_ACCOUNT_PATH = os.path.join(APIARY_ROOT, "serviceAccount.json")
DATABASE_URL = "https://apiary-750a9-default-rtdb.firebaseio.com/"
DB_PATH = os.path.join(APIARY_ROOT, "sovereign_core.db")

def log_ticket(agent, session_uuid, requested_path, status):
    timestamp = datetime.datetime.now().isoformat()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO ledger_tickets 
               (agent, session_uuid, requested_path, timestamp, status) 
               VALUES (?, ?, ?, ?, ?)""",
            (agent, session_uuid, requested_path, timestamp, status)
        )
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def process_ticket(key, data):
    if not isinstance(data, dict):
        return
    
    filepath = data.get('filepath')
    session_uuid = data.get('session_uuid')
    
    if not filepath or not session_uuid:
        print(f"[{key}] Invalid ticket payload.")
        return

    # Security check 1: Prevent UUID injection (Block directory traversal like ../)
    if not re.match(r"^[a-zA-Z0-9\-]{8,45}$", session_uuid):
        print(f"[{key}] Security Violation: Invalid UUID {session_uuid}")
        log_ticket("FERRIS", session_uuid, filepath, "REJECTED - INVALID UUID")
        return

    # Security check 2: Resolve symlinks before boundary check
    source_abs = os.path.realpath(os.path.join(APIARY_ROOT, filepath))
    if not source_abs.startswith(APIARY_ROOT + os.sep) and source_abs != APIARY_ROOT:
        print(f"[{key}] Security Violation: Attempted to access {source_abs}")
        log_ticket("FERRIS", session_uuid, filepath, "REJECTED - BOUNDARY VIOLATION")
        return
        
    # Security check 3: Allowlist
    if not any(source_abs.startswith(p + os.sep) or source_abs == p for p in ALLOWED_PREFIXES):
        print(f"[{key}] Security Violation: Not in Allowlist {source_abs}")
        log_ticket("FERRIS", session_uuid, filepath, "REJECTED - NOT IN ALLOWLIST")
        return
        
    if not os.path.exists(source_abs):
        print(f"[{key}] Error: File not found {source_abs}")
        log_ticket("FERRIS", session_uuid, filepath, "FAILED - NOT FOUND")
        return

    # Create safe target destination for Ferris
    agent_dir = os.path.join(APIARY_ROOT, "dna/agents/FERRIS/active_sessions", session_uuid)
    os.makedirs(agent_dir, exist_ok=True)
    
    target_abs = os.path.join(agent_dir, os.path.basename(source_abs))
    
    print(f"[{key}] Copying {source_abs} -> {target_abs}")
    try:
        shutil.copy2(source_abs, target_abs)
        log_ticket("FERRIS", session_uuid, filepath, "SUCCESS")
    except Exception as e:
        print(f"[{key}] Copy failed: {e}")
        log_ticket("FERRIS", session_uuid, filepath, f"FAILED - {str(e)}")

def on_queue_change(event):
    if event.data is None:
        return
        
    # Standardize processing: read the queue explicitly and clean it out
    ref = db.reference('import_queue/ferris')
    queue = ref.get()
    
    if queue and isinstance(queue, dict):
        for key, payload in queue.items():
            process_ticket(key, payload)
            # Delete ticket instantly (Airgap Rule 9)
            ref.child(key).delete()

def main():
    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        print(f"Missing {SERVICE_ACCOUNT_PATH}")
        sys.exit(1)

    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': DATABASE_URL
    })

    print("🚀 Initializing Firebase Dead-Drop Queue Listener on /import_queue/ferris...")
    _listener = db.reference('import_queue/ferris').listen(on_queue_change)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down listener...")

if __name__ == "__main__":
    main()
