#!/usr/bin/env python3
"""
Sovereign OS SDLC Completion Hook
Verifies the walkthrough artifact, computes MD5/size metadata, registers it in 
sys_attachment (with dynamic metadata columns), and reassigns the ticket to UAT.
"""

import sys
import os
import glob
import sqlite3
import uuid
import hashlib
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def compute_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def execute_completion_hook(ticket_id, walkthrough_path):
    ticket_id = ticket_id.strip().upper()
    
    # 1. Verify physical path & get metadata
    if not walkthrough_path or not os.path.exists(walkthrough_path):
        print(f"[Completion Hook Error] Walkthrough markdown file not found at: {walkthrough_path}")
        return False
        
    file_name = os.path.basename(walkthrough_path)
    file_size = os.path.getsize(walkthrough_path)
    md5_hash = compute_md5(walkthrough_path)
    sys_id = f"attach_{uuid.uuid4().hex}"
    
    print(f"[Completion Hook] Verified path: {walkthrough_path}")
    print(f"[Completion Hook] File size: {file_size} bytes | MD5: {md5_hash}")
    
    # 2. Database transaction
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cur = conn.cursor()
        
        # Dynamically ensure metadata columns exist
        cur.execute("PRAGMA table_info(sys_attachment)")
        cols = [col[1] for col in cur.fetchall()]
        if "md5_hash" not in cols:
            cur.execute("ALTER TABLE sys_attachment ADD COLUMN md5_hash TEXT")
        if "file_size" not in cols:
            cur.execute("ALTER TABLE sys_attachment ADD COLUMN file_size INTEGER")
            
        # Determine table_name and table_sys_id
        # Check if the ticket is in sovereign_tickets table
        cur.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ?", (ticket_id,))
        row = cur.fetchone()
        table_sys_id = row[0] if row else ticket_id
        
        table_name = 'sovereign_tickets'
        
        # Insert atomic row to sys_attachment
        cur.execute("""
            INSERT INTO sys_attachment (sys_id, table_name, table_sys_id, file_name, content_type, file_path, sys_created_on, md5_hash, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sys_id, table_name, table_sys_id, file_name, 'text/markdown', walkthrough_path, datetime.now().isoformat(), md5_hash, file_size))
        
        # Update the ticket state to 'Testing' and assigned_to to 'Vertex_UAT_Agent'
        work_notes_entry = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Development wrapped up. Walkthrough registered. MD5: {md5_hash}. Reassigned to Vertex_UAT_Agent for automated UAT validation."
        cur.execute("""
            UPDATE sovereign_tickets
            SET state = 'Testing', assigned_to = 'Vertex_UAT_Agent', work_notes = work_notes || ?, sys_updated_on = ?
            WHERE number = ?
        """, (work_notes_entry, datetime.now().isoformat(), ticket_id))
        
        conn.commit()
        conn.close()
        
        print(f"[Completion Hook Success] Walkthrough registered for {ticket_id}.")
        print(f"[Completion Hook Success] Reassigned {ticket_id} to 'Vertex_UAT_Agent' (State: 'Testing').")
        return True
    except Exception as e:
        print(f"[Completion Hook Exception] Database error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 sdlc_completion_hook.py <TICKET_ID> <WALKTHROUGH_PATH>")
        sys.exit(1)
        
    t_id = sys.argv[1]
    path = sys.argv[2]
    success = execute_completion_hook(t_id, path)
    sys.exit(0 if success else 1)
