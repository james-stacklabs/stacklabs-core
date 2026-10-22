#!/usr/bin/env python3
# ==============================================================================
# Sovereign OS: Staging Candidates Purge Daemon
# Path: /home/james/stacklabs/scripts/purge_staged_candidates.py
#
# Governed by WO-2026-0610-STAGING-PURGE.
# Scans staging buffers to purge unapproved candidate assets older than 24 hours
# while strictly preserving approved production assets.
# ==============================================================================

import os
import sys
import time
import argparse
import hashlib
import sqlite3
import uuid
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
LOG_PATH = "/home/james/stacklabs/logs/purge_daemon.log"

TARGET_DIRS = [
    "/home/james/stacklabs/work_orders/spark/media/staging",
    "/home/james/stacklabs/work_orders/spark/media",
    "/home/james/stacklabs/spark/media/staging",
    "/home/james/stacklabs/spark/media"
]

def get_md5(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return None

def get_sha256(filepath):
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return None

def load_database_safeguards():
    """Load hashes and filenames of production/finalized assets from SQLite tables."""
    safe_md5 = set()
    safe_sha256 = set()
    safe_filenames = set()

    if not os.path.exists(DB_PATH):
        print(f"[!] Database not found at {DB_PATH}. Running with minimal safeguards.")
        return safe_md5, safe_sha256, safe_filenames

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Read from sys_media_asset
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sys_media_asset'")
        if cursor.fetchone():
            cursor.execute("SELECT file_name, md5_hash FROM sys_media_asset")
            for filename, md5 in cursor.fetchall():
                if filename:
                    safe_filenames.add(filename.lower())
                if md5:
                    safe_md5.add(md5.lower())

        # 2. Read from cmdb_ci_media_asset
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cmdb_ci_media_asset'")
        if cursor.fetchone():
            cursor.execute("SELECT file_path, sha256 FROM cmdb_ci_media_asset")
            for file_path, sha256 in cursor.fetchall():
                if file_path:
                    safe_filenames.add(os.path.basename(file_path).lower())
                if sha256:
                    safe_sha256.add(sha256.lower())

        # 3. Read from spark_routing_receipts (defensive grace check)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='spark_routing_receipts'")
        if cursor.fetchone():
            cursor.execute("SELECT output_file, md5_hash, sha256_hash FROM spark_routing_receipts")
            for output_file, md5, sha256 in cursor.fetchall():
                if output_file:
                    safe_filenames.add(os.path.basename(output_file).lower())
                if md5:
                    safe_md5.add(md5.lower())
                if sha256:
                    safe_sha256.add(sha256.lower())

        conn.close()
    except Exception as e:
        print(f"[⚠️] Failed to load SQLite safeguards: {e}")

    return safe_md5, safe_sha256, safe_filenames

def run_purge(dry_run=False):
    print("[*] Initializing Staging Candidates Purge Daemon...")
    safe_md5, safe_sha256, safe_filenames = load_database_safeguards()

    now = time.time()
    cutoff_seconds = 24 * 3600
    cutoff_time = now - cutoff_seconds

    candidates = []
    total_bytes = 0

    for directory in TARGET_DIRS:
        if not os.path.exists(directory):
            continue
            
        print(f"[*] Scanning staging buffer: {directory}")
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            
            # Skip directories, check only files
            if not os.path.isfile(filepath):
                continue
                
            # Strict Continuity Safeguards
            # 1. State-freeze prefix check
            if filename.startswith("[PROCESSED]_"):
                continue
                
            # 2. Filename check
            if filename.lower() in safe_filenames:
                continue

            # Check age (> 24 hours)
            mtime = os.path.getmtime(filepath)
            if mtime < cutoff_time:
                # 3. Hash checks (MD5 & SHA256)
                file_md5 = get_md5(filepath)
                file_sha256 = get_sha256(filepath)
                
                if file_md5 and file_md5.lower() in safe_md5:
                    continue
                if file_sha256 and file_sha256.lower() in safe_sha256:
                    continue

                file_size = os.path.getsize(filepath)
                age_hours = (now - mtime) / 3600.0
                
                candidates.append({
                    "path": filepath,
                    "filename": filename,
                    "size": file_size,
                    "age_hours": age_hours
                })
                total_bytes += file_size

    total_mb = total_bytes / (1024.0 * 1024.0)

    if dry_run:
        print("\n=== DRY-RUN REPORT ===")
        print(f"Target files identified: {len(candidates)}")
        print(f"Projected storage savings: {total_mb:.2f} MB\n")
        print(f"{'Age (Hrs)':<10} | {'Size (MB)':<10} | {'File Path'}")
        print("-" * 80)
        for cand in candidates:
            size_mb = cand["size"] / (1024.0 * 1024.0)
            print(f"{cand['age_hours']:<10.1f} | {size_mb:<10.3f} | {cand['path']}")
        print("=======================")
        return

    # Active Execution
    deleted_count = 0
    reclaimed_bytes = 0

    for cand in candidates:
        try:
            os.remove(cand["path"])
            deleted_count += 1
            reclaimed_bytes += cand["size"]
            print(f"  [-] Purged: {cand['path']}")
        except Exception as e:
            print(f"  [❌] Failed to delete {cand['path']}: {e}")

    reclaimed_mb = reclaimed_bytes / (1024.0 * 1024.0)

    # 1. Append execution details to purge_daemon.log
    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp_str}] Deleted: {deleted_count} files | Reclaimed: {reclaimed_mb:.2f} MB\n"
    
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    try:
        with open(LOG_PATH, "a") as lf:
            lf.write(log_line)
    except Exception as e:
        print(f"[❌] Failed to write to log file: {e}")

    # 2. Log system maintenance event to ws_compliance_log in SQLite
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Verify ws_compliance_log table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ws_compliance_log'")
            if cursor.fetchone():
                sys_id = uuid.uuid4().hex
                batch_number = "WO-2026-0610-STAGING-PURGE"
                event_type = "SYSTEM_MAINTENANCE"
                description = f"Purged staging candidates: deleted {deleted_count} files, reclaimed {reclaimed_mb:.2f} MB."
                operator = "purge_staged_candidates"
                
                cursor.execute("""
                    INSERT INTO ws_compliance_log (sys_id, batch_number, event_type, description, operator)
                    VALUES (?, ?, ?, ?, ?)
                """, (sys_id, batch_number, event_type, description, operator))
                conn.commit()
                print("[✔] Logged maintenance event to SQLite central audit ledger.")
            
            conn.close()
        except Exception as e:
            print(f"[❌] Failed to log compliance event to DB: {e}")

    print(f"\n[✔] Active purge complete. Deleted {deleted_count} files, reclaimed {reclaimed_mb:.2f} MB.")

def main():
    parser = argparse.ArgumentParser(description="Purge staged unapproved candidate assets older than 24 hours.")
    parser.add_argument("--dry-run", action="store_true", help="List files and projected space savings without deleting.")
    args = parser.parse_args()
    
    run_purge(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
