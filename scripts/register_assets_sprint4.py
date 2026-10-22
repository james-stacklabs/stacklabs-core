#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import uuid
from datetime import datetime

SOVEREIGN_DB = "/home/james/stacklabs/dna/sovereign_now.db"
MAM_DB = "/home/james/stacklabs/dna/mam_warehouse.db"
TARGET_DIR = "/production/assets/sprint4"

# Mock MP4 header
MOCK_MP4_CONTENT = b"\x00\x00\x00\x1cftypmp42\x00\x00\x00\x00mp42isommp41\x00\x00\x00\x08freeMOCK"

assets = [
    {
        "name": "Rally Skeleton Dance",
        "file_name": "[PROCESSED]_RALLY_SKELETON_DANCE.mp4",
        "tag": "FS-MED-90117"
    },
    {
        "name": "Review In Progress",
        "file_name": "[PROCESSED]_REVIEW_IN_PROGRESS.mp4",
        "tag": "FS-MED-90118"
    },
    {
        "name": "Level 3 Tension",
        "file_name": "[PROCESSED]_LEVEL_3_TENSION.mp4",
        "tag": "FS-MED-90119"
    }
]

def main():
    print("[*] Creating directory if not exists...")
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # 1. Connect to DBs
    conn_sov = sqlite3.connect(SOVEREIGN_DB)
    curr_sov = conn_sov.cursor()
    
    conn_mam = sqlite3.connect(MAM_DB)
    curr_mam = conn_mam.cursor()
    
    for a in assets:
        file_path = os.path.join(TARGET_DIR, a["file_name"])
        print(f"[*] Staging placeholder file: {file_path}")
        
        # Write mock MP4 with unique trailing bytes to prevent MD5 collisions
        content = MOCK_MP4_CONTENT + a["name"].encode()
        with open(file_path, "wb") as f:
            f.write(content)
            
        # Calculate size & hashes
        size = len(content)
        md5_val = hashlib.md5(content).hexdigest()
        sha256_val = hashlib.sha256(content).hexdigest()
        
        sys_id = str(uuid.uuid4()).replace('-', '')
        
        # Register in sovereign_now.db (sys_media_asset)
        try:
            curr_sov.execute("""
                INSERT OR REPLACE INTO sys_media_asset (
                    sys_id, asset_tag, name, file_name, file_path, 
                    file_size_bytes, mime_type, category, status, md5_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
            """, (sys_id, a["tag"], a["name"], a["file_name"], file_path, size, "video/mp4", "Sprint 4 Overlays", md5_val))
            print(f"  [+] Registered in sys_media_asset as {a['tag']}")
        except Exception as e:
            print(f"  [-] Failed sys_media_asset insertion: {e}")
            
        # Register in mam_warehouse.db (media_assets)
        try:
            curr_mam.execute("""
                INSERT OR REPLACE INTO media_assets (
                    asset_id, file_path, mime_type, created_at
                ) VALUES (?, ?, ?, ?)
            """, (sys_id, file_path, "video/mp4", datetime.utcnow().isoformat()))
            
            # Clean old metadata
            curr_mam.execute("DELETE FROM asset_metadata WHERE asset_id = ?", (sys_id,))
            
            # Metadata entries
            meta_pairs = [
                ("size_bytes", str(size)),
                ("md5", md5_val),
                ("sha256", sha256_val),
                ("width", "1920"),
                ("height", "1080"),
                ("duration", "10.0")
            ]
            for key, val in meta_pairs:
                curr_mam.execute("""
                    INSERT INTO asset_metadata (asset_id, key, value)
                    VALUES (?, ?, ?)
                """, (sys_id, key, f'"{val}"'))
                
            print(f"  [+] Registered in mam_warehouse.db as asset {sys_id}")
        except Exception as e:
            print(f"  [-] Failed mam_warehouse.db insertion: {e}")
            
    conn_sov.commit()
    conn_sov.close()
    
    conn_mam.commit()
    conn_mam.close()
    print("[*] Sprint 4 Asset Registration complete.")

if __name__ == "__main__":
    main()
