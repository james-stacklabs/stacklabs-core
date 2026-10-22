#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import uuid
import shutil
import re
import time

# Database paths to synchronize
DB_PATHS = [
    "/home/james/stacklabs/dna/sovereign_now.db",
    "/home/james/stacklabs-sandbox/dna/sovereign_now.db"
]

MEDIA_VAULT_ROOT = "/home/james/stacklabs/media_vault"
INCOMING_DIR = "/home/james/stacklabs-sandbox/catnip_wars_incoming/flow assest"
TARGET_DIR = os.path.join(MEDIA_VAULT_ROOT, "01_Assets/Catnip_Wars")

def execute_with_retry(db_path, query, params=(), is_write=False, fetch_one=False, fetch_all=False):
    """Executes a SQLite query with robust lock-handling and retries."""
    max_retries = 5
    delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # Set a long timeout for concurrent lock releases
            conn = sqlite3.connect(db_path, timeout=30.0)
            cursor = conn.cursor()
            
            cursor.execute(query, params)
            
            result = None
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
                
            if is_write:
                conn.commit()
                
            conn.close()
            return result
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                print(f"  [!] Database {os.path.basename(db_path)} is locked. Retrying in {delay}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(delay)
                delay *= 2
            else:
                raise e

def create_table_if_missing(db_path):
    """Ensures the sys_media_asset CMDB table exists."""
    if not os.path.exists(os.path.dirname(db_path)):
        return False
    
    # sys_media_asset table schema (ServiceNow asset structure)
    execute_with_retry(
        db_path,
        """
        CREATE TABLE IF NOT EXISTS sys_media_asset (
            sys_id           TEXT PRIMARY KEY,
            asset_tag        TEXT UNIQUE NOT NULL,
            name             TEXT NOT NULL,
            file_name        TEXT NOT NULL,
            file_path        TEXT NOT NULL,
            file_size_bytes  INTEGER NOT NULL,
            mime_type        TEXT NOT NULL,
            category         TEXT NOT NULL,
            status           TEXT DEFAULT 'Active',
            md5_hash         TEXT UNIQUE,
            created_at       TEXT DEFAULT (datetime('now')),
            updated_at       TEXT DEFAULT (datetime('now'))
        );
        """,
        is_write=True
    )
    return True

def get_md5(filepath):
    """Calculates MD5 hash of the file to verify uniqueness."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def clean_filename(name):
    """Cleans up ellipsis and weird characters in incoming filenames."""
    # Replace unicode ellipsis
    name = name.replace("\u2026", "")
    name = name.replace("…", "")
    # Clean up double underscores
    name = re.sub(r'_{2,}', '_', name)
    return name

def get_mime_type(filename):
    """Simple mime type resolution based on file extension."""
    ext = os.path.splitext(filename.lower())[1]
    if ext in ('.png', '.png_202605241941.jpeg'):
        return 'image/png'
    if ext in ('.jpg', '.jpeg'):
        return 'image/jpeg'
    if ext == '.svg':
        return 'image/svg+xml'
    return 'application/octet-stream'

def generate_next_asset_tag(db_path):
    """Generates the next sequential asset tag FS-MED-XXXXX."""
    row = execute_with_retry(
        db_path,
        "SELECT asset_tag FROM sys_media_asset ORDER BY asset_tag DESC LIMIT 1",
        fetch_one=True
    )
    if row:
        last_tag = row[0]
        # Extract numeric suffix from FS-MED-XXXXX
        match = re.search(r'FS-MED-(\d+)', last_tag)
        if match:
            next_num = int(match.group(1)) + 1
            return f"FS-MED-{next_num:05d}"
    return "FS-MED-00001"

def register_file(db_path, filepath, category):
    """Surgically registers a file in the sys_media_asset table."""
    file_name = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)
    md5 = get_md5(filepath)
    mime = get_mime_type(file_name)
    
    # Check if this file hash already exists to prevent duplicate entries
    existing = execute_with_retry(
        db_path,
        "SELECT sys_id, asset_tag, name FROM sys_media_asset WHERE md5_hash = ?",
        (md5,),
        fetch_one=True
    )
    if existing:
        print(f"  [~] File {file_name} already registered as {existing[1]} ({existing[2]}) - skipping.")
        return existing[0]
        
    # Generate new UUID and asset tag
    sys_id = str(uuid.uuid4()).replace('-', '')
    tag = generate_next_asset_tag(db_path)
    
    # Format a beautiful display name from the filename
    name_clean = os.path.splitext(file_name)[0]
    name_clean = name_clean.replace('_', ' ').replace('-', ' ').title()
    # Strip dates and hashes for clean names
    name_clean = re.sub(r'\d{12}.*', '', name_clean).strip()
    
    execute_with_retry(
        db_path,
        """
        INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, md5_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (sys_id, tag, name_clean, file_name, filepath, file_size, mime, category, md5),
        is_write=True
    )
    
    print(f"  [+] Registered: {tag} | {name_clean} | Size: {file_size} bytes")
    return sys_id

def main():
    print("==================================================================")
    print("      🧬 SOVEREIGN OS CMDB: MEDIA VAULT REGISTRATION SYSTEM")
    print("==================================================================")
    
    # 1. Initialize Tables in all databases
    active_dbs = []
    for db in DB_PATHS:
        try:
            if create_table_if_missing(db):
                print(f"[*] Initialized sys_media_asset schema in: {db}")
                active_dbs.append(db)
        except Exception as e:
            print(f"[-] Failed to initialize database {db}: {e}")
            
    # 2. Process incoming sandbox files
    if os.path.exists(INCOMING_DIR):
        print(f"\n[*] Scanning incoming files in: {INCOMING_DIR}")
        os.makedirs(TARGET_DIR, exist_ok=True)
        
        for file in os.listdir(INCOMING_DIR):
            incoming_path = os.path.join(INCOMING_DIR, file)
            if os.path.isfile(incoming_path):
                clean_name = clean_filename(file)
                target_path = os.path.join(TARGET_DIR, clean_name)
                
                # Copy file into structured media vault
                shutil.copy2(incoming_path, target_path)
                print(f"  -> Cooled and Copied: {clean_name}")
                
                # Register file in all databases
                for db in active_dbs:
                    try:
                        register_file(db, target_path, "Catnip Wars")
                    except Exception as e:
                        print(f"  [-] Failed registration in {db}: {e}")
                    
        # 3. Clean up the incoming sandbox folder completely (Zero-Litter compliance)
        try:
            shutil.rmtree(INCOMING_DIR)
            print(f"\n[+] Incoming sandbox folder cleaned up completely.")
        except Exception as e:
            print(f"[-] Warning: Failed to clean sandbox folder: {e}")
        
    # 4. Perform inventory sweep on existing media vault files to register them
    print("\n[*] Performing full inventory sweep of existing media vault folders...")
    sweep_dirs = [
        (os.path.join(MEDIA_VAULT_ROOT, "01_Assets"), "FanStack Assets"),
        (os.path.join(MEDIA_VAULT_ROOT, "03_Assets"), "FanStack Personas")
    ]
    
    for folder, category in sweep_dirs:
        if os.path.exists(folder):
            for root, _, files in os.walk(folder):
                # Skip the Catnip Wars folder we just manually processed
                if "Catnip_Wars" in root:
                    continue
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.gif')):
                        filepath = os.path.join(root, file)
                        for db in active_dbs:
                            try:
                                register_file(db, filepath, category)
                            except Exception as e:
                                pass
                            
    print("\n==================================================================")
    print("      [+] MEDIA VAULT CMDB REGISTRATION COMPLETE!")
    print("==================================================================")

if __name__ == "__main__":
    main()
