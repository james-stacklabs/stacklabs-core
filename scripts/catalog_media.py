#!/usr/bin/env python3
# ==============================================================================
# Sovereign OS - Media Cataloger (WO-2026-115)
# Indexes media assets from media_stack/assets/live into cmdb_ci_media_asset
# ==============================================================================
import os
import re
import sqlite3
import hashlib
import uuid
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
REPO_ROOT = "/home/james/stacklabs"
PITCHES_DIR = os.path.join(REPO_ROOT, "media_stack/assets/live/pitches")
BRAND_DIR = os.path.join(REPO_ROOT, "media_stack/assets/live/brand")

SUPPORTED_EXTENSIONS = {".mp4", ".png", ".jpg", ".jpeg", ".gif", ".mov", ".avi"}

def compute_sha256(filepath):
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"Error computing hash for {filepath}: {e}")
        return None

def parse_filename(filename, dir_name):
    # Strip extension
    base_name, _ = os.path.splitext(filename)
    
    # Check if there are underscores
    tokens = base_name.split("_")
    
    # Clean version suffix (e.g. _v1, _v2, etc.) at the end
    if len(tokens) > 1 and re.match(r'^v\d+$', tokens[-1]):
        tokens = tokens[:-1]
    
    if not tokens or (len(tokens) == 1 and tokens[0] == ""):
        return dir_name, "default"
        
    first_token = tokens[0]
    
    # If first token is numeric (player/pitcher ID)
    if first_token.isdigit():
        advocate = first_token
        expression = "_".join(tokens[1:]) if len(tokens) > 1 else "default"
    else:
        advocate = first_token
        expression = "_".join(tokens[1:]) if len(tokens) > 1 else "default"
        
    if not expression:
        expression = "default"
        
    return advocate, expression

def catalog_directory(conn, dir_path, dir_label):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        print(f"Created target directory: {dir_path}")
        return

    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for entry in os.scandir(dir_path):
        if entry.is_file():
            _, ext = os.path.splitext(entry.name)
            if ext.lower() not in SUPPORTED_EXTENSIONS:
                continue

            file_abs_path = entry.path
            # Store the relative path from the repo root starting with /media_stack/
            file_rel_path = "/" + os.path.relpath(file_abs_path, REPO_ROOT)
            
            sha256 = compute_sha256(file_abs_path)
            if not sha256:
                continue

            advocate, expression = parse_filename(entry.name, dir_label)

            # Check if record exists
            cursor.execute(
                "SELECT sys_id, sha256, advocate, expression FROM cmdb_ci_media_asset WHERE file_path = ?",
                (file_rel_path,)
            )
            row = cursor.fetchone()

            if row:
                sys_id, existing_sha256, existing_adv, existing_exp = row
                # If hash or metadata changed, update it
                if (existing_sha256 != sha256 or 
                    existing_adv != advocate or 
                    existing_exp != expression):
                    cursor.execute(
                        """
                        UPDATE cmdb_ci_media_asset
                        SET sha256 = ?, advocate = ?, expression = ?, sys_updated_on = ?
                        WHERE sys_id = ?
                        """,
                        (sha256, advocate, expression, now_str, sys_id)
                    )
                    print(f"🔄 Updated asset in SQLite: {file_rel_path} -> advocate: {advocate}, expression: {expression}")
            else:
                # Insert new asset record
                new_sys_id = uuid.uuid4().hex
                cursor.execute(
                    """
                    INSERT INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256, sys_created_on, sys_updated_on)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (new_sys_id, advocate, expression, file_rel_path, sha256, now_str, now_str)
                )
                print(f"🆕 Registered new asset in SQLite: {file_rel_path} -> advocate: {advocate}, expression: {expression}")

def main():
    print("🎬 Commencing media cataloging pass...")
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        catalog_directory(conn, PITCHES_DIR, "pitches")
        catalog_directory(conn, BRAND_DIR, "brand")
        conn.commit()
        conn.close()
        print("🟢 SUCCESS: Media cataloging pass completed.")
    except Exception as e:
        print(f"❌ ERROR: Media cataloger failed: {e}")

if __name__ == "__main__":
    main()
