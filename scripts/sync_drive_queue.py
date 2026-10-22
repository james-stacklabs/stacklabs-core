#!/usr/bin/env python3
"""
Sovereign OS: Drive Queue Sync Courier Daemon
Path: /home/james/stacklabs/scripts/sync_drive_queue.py
Governing Standard: Invariant 35 & WO0010971

Monitors Google Drive (stacklabs_edge:StackLabs/Queue/Incoming/) for 4-Quarters Work Orders
drafted by Spark/Gemini, validates local deduplication on Clio metal, drops fresh tickets
into queue/incoming/, and pushes completed archives and execution logs back to Drive.
"""

import os
import sys
import fcntl
import re
import time
import shutil
import hashlib
import logging
import argparse
import subprocess
from pathlib import Path
from typing import List, Set, Optional

# Enforce Canonical Environment
STACKLABS_ROOT = Path("/home/james/stacklabs")
if str(STACKLABS_ROOT) not in sys.path:
    sys.path.insert(0, str(STACKLABS_ROOT))

# Local Paths
QUEUE_DIR = STACKLABS_ROOT / "queue"
LOCAL_INCOMING = QUEUE_DIR / "incoming"
LOCAL_PROCESSING = QUEUE_DIR / "processing"
LOCAL_ARCHIVE = QUEUE_DIR / "archive"
LOCAL_FAILED = QUEUE_DIR / "failed"
LOCAL_LOGS = QUEUE_DIR / "logs"
LOG_DIR = STACKLABS_ROOT / "logs"
LOG_FILE = LOG_DIR / "sync_drive_queue.log"
LOCK_FILE = QUEUE_DIR / ".sync_drive.lock"

# Remote Google Drive Targets
REMOTE_BASE = "stacklabs_edge:StackLabs/Queue"
REMOTE_INCOMING = f"{REMOTE_BASE}/Incoming"
REMOTE_ARCHIVE = f"{REMOTE_BASE}/Archive"
REMOTE_LOGS = f"{REMOTE_BASE}/Logs"

# Logging Setup
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_INCOMING.mkdir(parents=True, exist_ok=True)
LOCAL_ARCHIVE.mkdir(parents=True, exist_ok=True)
LOCAL_LOGS.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("DriveQueueSync")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] [COURIER] %(message)s")

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
fh.setFormatter(formatter)
logger.addHandler(fh)


def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


archive_hash_cache = {}


def get_local_archived_hashes() -> Set[str]:
    """Collect SHA-256 hashes of all archived work orders on Clio (Dogfood: mtime cache)."""
    global archive_hash_cache
    hashes = set()
    if not LOCAL_ARCHIVE.exists():
        return hashes
    for f in LOCAL_ARCHIVE.glob("*.md"):
        try:
            mtime = f.stat().st_mtime
            cached = archive_hash_cache.get(f)
            if cached and cached[0] == mtime:
                hashes.add(cached[1])
            else:
                h = calculate_sha256(f)
                if h:
                    archive_hash_cache[f] = (mtime, h)
                    hashes.add(h)
        except Exception:
            continue
    return hashes


def extract_ticket_id(filename: str, content: str = "") -> str:
    """Extract canonical ticket ID (e.g. WO0010970) from filename or content."""
    m = re.search(r'\b((?:WO|STRY|INC|DFCT|ENHC|REQ)[-_]?\d+)\b', filename, re.IGNORECASE)
    if m:
        return m.group(1).upper().replace('-', '')
    if content:
        m2 = re.search(r'\b(?:Ticket ID|Ticket|Work Order ID)\b[\s*:\`]*([A-Za-z0-9\-_]+)', content, re.IGNORECASE)
        if m2:
            sub = re.match(r'^((?:WO|STRY|INC|DFCT|ENHC|REQ)[-_]?\d+)', m2.group(1).strip(), re.IGNORECASE)
            if sub:
                return sub.group(1).upper().replace('-', '')
    return ""


def is_ticket_already_on_metal(ticket_id: str, content_hash: str, archived_hashes: Set[str]) -> bool:
    """
    Check if a ticket is already archived, processing, or resolved on Clio metal.
    Protects against dual-ingress split-brain race conditions.
    """
    if not ticket_id and not content_hash:
        return False

    # 1. Content hash check
    if content_hash and content_hash in archived_hashes:
        return True

    # 2. Check archive directory for ticket ID in filename
    if ticket_id:
        for f in LOCAL_ARCHIVE.glob("*.md"):
            if ticket_id in f.name.upper():
                return True
        for f in LOCAL_PROCESSING.glob("*.md"):
            if ticket_id in f.name.upper():
                return True

    # 3. Check SQLite Ground Truth DB if available
    db_path = STACKLABS_ROOT / "ground_truth" / "ground_truth.db"
    if db_path.exists() and ticket_id:
        try:
            import sqlite3
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM sovereign_tickets WHERE number = ? AND state_int >= 4 LIMIT 1", (ticket_id,))
                if cursor.fetchone():
                    return True
        except Exception:
            pass

    return False


def run_rclone(cmd_args: List[str], timeout: int = 45) -> subprocess.CompletedProcess:
    """Run an rclone command with standardized timeout and error handling."""
    full_cmd = ["rclone"] + cmd_args
    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)


def verify_remote_structure():
    """Ensure remote Queue directories exist on Google Drive."""
    for remote_dir in [REMOTE_INCOMING, REMOTE_ARCHIVE, REMOTE_LOGS]:
        try:
            run_rclone(["mkdir", remote_dir], timeout=20)
        except Exception as e:
            logger.warning(f"Could not verify remote directory {remote_dir}: {e}")


def pull_incoming_tickets():
    """
    Pull pending .md Work Orders from Google Drive Incoming.
    Applies strict deduplication: if already executed locally, auto-archives remote file.
    """
    try:
        res = run_rclone(["lsf", "--files-only", REMOTE_INCOMING], timeout=20)
        if res.returncode != 0:
            return
        remote_files = [f.strip() for f in res.stdout.splitlines() if f.strip() and f.strip().endswith(".md")]
        if not remote_files:
            return

        archived_hashes = get_local_archived_hashes()

        for filename in remote_files:
            remote_path = f"{REMOTE_INCOMING}/{filename}"
            tmp_download = Path(f"/tmp/{filename}")

            # Download temporarily to inspect
            dl_res = run_rclone(["copyto", remote_path, str(tmp_download)], timeout=30)
            if dl_res.returncode != 0 or not tmp_download.exists():
                logger.error(f"Failed to download remote candidate {filename}: {dl_res.stderr}")
                continue

            content = tmp_download.read_text(encoding="utf-8", errors="ignore")
            content_hash = calculate_sha256(tmp_download)
            ticket_id = extract_ticket_id(filename, content)

            # Deduplication Check
            if is_ticket_already_on_metal(ticket_id, content_hash, archived_hashes):
                logger.info(f"⚡ [DEDUP] Ticket {ticket_id or filename} already executed on metal. Auto-archiving on Drive...")
                run_rclone(["moveto", remote_path, f"{REMOTE_ARCHIVE}/{filename}"], timeout=30)
                if tmp_download.exists():
                    tmp_download.unlink()
                continue

            # Fresh Ticket: Stage to Clio incoming
            target_local = LOCAL_INCOMING / filename
            shutil.move(str(tmp_download), str(target_local))
            logger.info(f"📥 [INGEST] Staged fresh Work Order from Drive to Clio metal: {filename}")

            # Move remote file from Incoming to Archive on Drive so it does not pull again
            run_rclone(["moveto", remote_path, f"{REMOTE_ARCHIVE}/{filename}"], timeout=30)

    except subprocess.TimeoutExpired:
        logger.warning("rclone timed out during pull_incoming_tickets")
    except Exception as e:
        logger.error(f"Error in pull_incoming_tickets: {e}")


def push_receipts_and_logs():
    """
    Push completed Work Orders and execution logs from Clio metal to Google Drive.
    Uses --update to ensure only new or modified files are uploaded.
    """
    try:
        # 1. Sync archive Work Orders
        res_arch = run_rclone(["copy", "--update", "--max-age", "48h", str(LOCAL_ARCHIVE), REMOTE_ARCHIVE], timeout=45)
        if res_arch.returncode != 0 and res_arch.stderr:
            logger.warning(f"Notice during archive push: {res_arch.stderr.strip()}")

        # 2. Sync execution logs
        res_logs = run_rclone(["copy", "--update", "--max-age", "48h", str(LOCAL_LOGS), REMOTE_LOGS], timeout=45)
        if res_logs.returncode != 0 and res_logs.stderr:
            logger.warning(f"Notice during logs push: {res_logs.stderr.strip()}")

    except subprocess.TimeoutExpired:
        logger.warning("rclone timed out during push_receipts_and_logs")
    except Exception as e:
        logger.error(f"Error in push_receipts_and_logs: {e}")


def run_cycle():
    """Execute one full synchronization cycle."""
    pull_incoming_tickets()
    push_receipts_and_logs()


def main():
    parser = argparse.ArgumentParser(description="Drive Queue Sync Courier Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single sync cycle and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as a background daemon")
    parser.add_argument("--interval", type=int, default=15, help="Polling interval in seconds (default: 15)")
    args = parser.parse_args()

    # Concurrency Lock
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.info("Another instance of sync_drive_queue is already active. Exiting.")
        sys.exit(0)

    logger.info("🚀 Starting Drive Queue Sync Courier...")
    verify_remote_structure()

    if args.once or not args.daemon:
        run_cycle()
        logger.info("✔ Single sync cycle complete.")
        return

    logger.info(f"🔄 Running daemon mode with {args.interval}s polling interval...")
    while True:
        try:
            run_cycle()
        except Exception as e:
            logger.error(f"Unexpected error in daemon loop: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
