#!/usr/bin/env python3
# ==============================================================================
# Sovereign OS: Staging Images Purge Engine (Cron Utility)
# Path: /home/james/stacklabs/scripts/purge_staging_images.py
#
# Governed by WO-2026-0610 / INC1573651.
# Scans /home/james/sovereign_inbox/staging/ and purges directories older
# than 24 hours. Marks expired database entries accordingly.
# ==============================================================================

import os
import time
import shutil
import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
STAGING_DIR = "/home/james/sovereign_inbox/staging"

def purge_expired_staging():
    print("[*] Initiating Staging Image Purge Sequence...")
    if not os.path.exists(STAGING_DIR):
        print("[i] Staging directory does not exist. Skipping.")
        return
        
    now = time.time()
    cutoff = now - (24 * 3600)  # 24 hours ago
    
    purged_count = 0
    expired_ids = []
    
    # Iterate over items in the staging directory
    for item in os.listdir(STAGING_DIR):
        item_path = os.path.join(STAGING_DIR, item)
        if not os.path.isdir(item_path):
            continue
            
        # Get creation/modification time of the directory
        mtime = os.path.getmtime(item_path)
        if mtime < cutoff:
            print(f"  [-] Directory {item} is older than 24 hours. Purging...")
            try:
                shutil.rmtree(item_path)
                purged_count += 1
                expired_ids.append(item)
            except Exception as e:
                print(f"  [❌] Failed to remove {item_path}: {e}")
                
    # Update SQLite database for expired entries
    if expired_ids and os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for sys_id in expired_ids:
                cursor.execute("""
                    UPDATE sys_omega_gate_backlog
                    SET status = 'EXPIRED', updated_at = CURRENT_TIMESTAMP
                    WHERE sys_id = ? AND status = 'PENDING'
                """, (sys_id,))
            conn.commit()
            conn.close()
            print(f"[✔] Successfully marked {len(expired_ids)} backlog entries as EXPIRED in DB.")
        except Exception as e:
            print(f"[❌] Database update failure: {e}")
            
    print(f"[✔] Staging purge complete. {purged_count} directories cleaned up.")

if __name__ == "__main__":
    purge_expired_staging()
