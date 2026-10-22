#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import uuid
import base64
import shutil
import re
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
TICKET_ID = "STRY1789561"

SRC_DIR = "/home/james/sovereign_inbox/pilot_drops/Metsy Prime"
FANSTACK_LOOKBOOK_DIR = "/home/james/stacklabs/15_FanStack/public/lookbook/metsy"
MEDIA_VAULT_DIR = "/home/james/stacklabs/media_vault/01_Assets/Metsy_Lookbook"

def get_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def get_sha256(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def generate_next_asset_tag(cursor):
    cursor.execute("SELECT asset_tag FROM sys_media_asset")
    rows = cursor.fetchall()
    max_num = 0
    for row in rows:
        tag = row[0]
        if tag:
            match = re.search(r'FS-MED-(\d+)', tag)
            if match:
                num = int(match.group(1))
                if num < 99999: # Ignore test/out-of-bounds tags
                    if num > max_num:
                        max_num = num
    next_num = max_num + 1
    return f"FS-MED-{next_num:05d}"

def get_mime_type(ext):
    ext = ext.lower()
    if ext == '.png':
        return 'image/png'
    elif ext in ['.jpg', '.jpeg']:
        return 'image/jpeg'
    elif ext == '.jfif':
        return 'image/jfif'
    elif ext == '.mp4':
        return 'video/mp4'
    else:
        return 'application/octet-stream'

def get_category(filename, expr_name):
    lower_name = filename.lower()
    lower_expr = expr_name.lower()
    if 'concept' in lower_name or 'concept' in lower_expr or 'grid' in lower_name:
        return 'Concept Art'
    elif 'adventure' in lower_name or 'adventure' in lower_expr:
        return 'Adventures'
    else:
        return 'Raw Photos'

def main():
    print("==================================================================")
    print(f"🚀 Initializing Ingestion for Metsy Lookbook: {TICKET_ID}")
    print("==================================================================")

    if not os.path.exists(SRC_DIR):
        print(f"[-] ERROR: Source directory not found: {SRC_DIR}")
        return

    os.makedirs(FANSTACK_LOOKBOOK_DIR, exist_ok=True)
    os.makedirs(MEDIA_VAULT_DIR, exist_ok=True)

    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Verify ticket state set to Work in Progress (2)
    cursor.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ?", (TICKET_ID,))
    ticket_row = cursor.fetchone()
    if ticket_row:
        ticket_sys_id = ticket_row[0]
        cursor.execute("""
            UPDATE sovereign_tickets 
            SET state = 2, work_notes = work_notes || '\n[Ingest]: Commenced ingestion of Metsy lookbook drops.' 
            WHERE sys_id = ?
        """, (ticket_sys_id,))
    else:
        ticket_sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes)
            VALUES (?, ?, 'STRY', 'Create Metsy Lookbook of Catnip Wars pictures', 'Assemble a digital lookbook featuring all Metsy character images generated since the Catnip Wars session.', 2, 2, 'antigravity', 'cmdb_ci_media_asset', 'Ticket initialized by lookbook ingestion daemon.')
        """, (ticket_sys_id, TICKET_ID))
    conn.commit()

    files = [f for f in os.listdir(SRC_DIR) if os.path.isfile(os.path.join(SRC_DIR, f))]
    print(f"[*] Found {len(files)} files to ingest.")

    ingested_details = []

    for filename in sorted(files):
        src_path = os.path.join(SRC_DIR, filename)
        
        # Determine expression name
        base, ext = os.path.splitext(filename)
        expr_name = base.replace(' ', '_')
        
        # Mappings
        fanstack_path = os.path.join(FANSTACK_LOOKBOOK_DIR, filename)
        vault_path = os.path.join(MEDIA_VAULT_DIR, filename)
        
        # Copy to FanStack and Media Vault
        shutil.copy2(src_path, fanstack_path)
        shutil.copy2(src_path, vault_path)
        
        file_size = os.path.getsize(fanstack_path)
        md5_hash = get_md5(fanstack_path)
        sha256_hash = get_sha256(fanstack_path)
        
        with open(fanstack_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            
        mime = get_mime_type(ext)
        category = get_category(filename, expr_name)
        
        # Check if asset exists in sys_media_asset
        cursor.execute("SELECT sys_id FROM sys_media_asset WHERE md5_hash = ?", (md5_hash,))
        existing_asset = cursor.fetchone()
        
        if existing_asset:
            asset_sys_id = existing_asset[0]
            cursor.execute("""
                UPDATE sys_media_asset
                SET name = ?, file_name = ?, file_path = ?, file_size_bytes = ?, mime_type = ?, category = ?, image_blob = ?, updated_at = datetime('now')
                WHERE sys_id = ?
            """, (f"Metsy Lookbook ({expr_name})", filename, fanstack_path, file_size, mime, category, b64, asset_sys_id))
            cursor.execute("SELECT asset_tag FROM sys_media_asset WHERE sys_id = ?", (asset_sys_id,))
            asset_tag = cursor.fetchone()[0]
        else:
            asset_tag = generate_next_asset_tag(cursor)
            asset_sys_id = uuid.uuid4().hex
            cursor.execute("""
                INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
            """, (asset_sys_id, asset_tag, f"Metsy Lookbook ({expr_name})", filename, fanstack_path, file_size, mime, category, md5_hash, b64))
            
        # Register in cmdb_ci_media_asset
        web_path = f"/lookbook/metsy/{filename}"
        cursor.execute("DELETE FROM cmdb_ci_media_asset WHERE advocate = 'metsy' AND expression = ?", (expr_name,))
        cursor.execute("""
            INSERT INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
            VALUES (?, 'metsy', ?, ?, ?)
        """, (uuid.uuid4().hex, expr_name, web_path, sha256_hash))
        
        conn.commit()
        print(f"  [+] Ingested {filename} -> Tag: {asset_tag}, Category: {category}")
        ingested_details.append(f"- {filename} ({asset_tag}) -> Category: {category}")

    # Set ticket state to Resolved (4) as task is completed for ingestion side (the rest resolved at the end)
    print("[*] Updating database with lookbook logs...")
    work_notes_entry = "\n[Ingest Complete]: Successfully processed lookbook files:\n" + "\n".join(ingested_details)
    cursor.execute("""
        UPDATE sovereign_tickets 
        SET work_notes = work_notes || ? 
        WHERE sys_id = ?
    """, (work_notes_entry, ticket_sys_id))
    
    conn.commit()
    conn.close()

    print("==================================================================")
    print("🟢 SUCCESS: Metsy lookbook ingestion complete!")
    print("==================================================================")

if __name__ == "__main__":
    main()
