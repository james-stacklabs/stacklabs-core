#!/usr/bin/env python3
"""
Sovereign OS Scratchpad & Pilot Drops Poller
Monitors /home/james/stacklabs/pilot_drops/scratch_pad.md and pilot_drops/
for incoming work orders from the Pilot (Artemis / Mobile).
Exits with 0 and prints order details when a new task or change is detected,
triggering immediate reactive wakeup for autonomous Clio execution.
"""

import argparse
import difflib
import hashlib
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Paths
SOVEREIGN_ROOT = Path(__file__).resolve().parents[1]
INBOX_ROOT = Path("/home/james/stacklabs")
PILOT_DROPS_DIR = INBOX_ROOT / "pilot_drops"
SCRATCH_PAD_PATH = PILOT_DROPS_DIR / "scratch_pad.md"
LOG_PATH = SOVEREIGN_ROOT / "logs" / "scratch_pad_poller.log"

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SCRATCHPAD_POLLER] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("scratch_pad_poller")


def compute_hash(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"Error computing hash for {path}: {e}")
        return ""


def read_content(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")
        return ""


def get_known_files(directory: Path) -> dict:
    files = {}
    if not directory.exists():
        return files
    for p in directory.glob("*.md"):
        if p.name == "scratch_pad.md":
            continue
        try:
            files[str(p)] = p.stat().st_mtime
        except Exception:
            pass
    return files


def ensure_ticket_registered(task_text: str):
    """Auto-ingest ticket into sovereign_now.db via FastAPI if not already registered."""
    m = re.search(r'\b((?:WO|STRY|DFCT|ENHC|REQ|INC|PRB|CHG)\d+[A-Za-z0-9_-]*)\b', task_text)
    if not m:
        return
    ticket_id = m.group(1)

    # Check if ticket already exists
    try:
        check_url = f"http://127.0.0.1:8095/api/tickets/{urllib.parse.quote(ticket_id)}"
        req = urllib.request.Request(check_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            if data.get("id") or data.get("number"):
                logger.info(f"Verified ticket {ticket_id} already registered in SDLC ledger.")
                return
    except urllib.error.HTTPError as e:
        if e.code != 404:
            logger.warning(f"Error checking ticket {ticket_id}: {e}")
    except Exception as e:
        logger.warning(f"Failed to check ticket {ticket_id}: {e}")

    # Extract clean title from header
    title = f"Task: {ticket_id}"
    for line in task_text.splitlines():
        if line.startswith("### "):
            raw = line.replace("### ", "").strip()
            raw = re.sub(r'\[.*?\]', '', raw).strip()
            title = re.sub(r'^(?:TASK\s+\d+:?\s*)', '', raw).strip()
            break

    # Extract Affected CI
    ci = "sovereign_knot_core"
    ci_match = re.search(r'Affected CI[:\s]+`?([a-zA-Z0-9_-]+)`?', task_text)
    if ci_match:
        ci = ci_match.group(1)

    # Map ticket type
    prefix = ticket_id[:2]
    ticket_type = "Work Order"
    if prefix == "ST":
        ticket_type = "Story"
    elif prefix == "DF":
        ticket_type = "Defect"
    elif prefix == "EN":
        ticket_type = "Enhancement"
    elif prefix == "RE":
        ticket_type = "Request"

    payload = {
        "number": ticket_id,
        "ticket_type": ticket_type,
        "title": title,
        "description": task_text[:1200],
        "affected_ci": ci,
        "status": "OPEN",
        "priority": "P2"
    }

    try:
        post_req = urllib.request.Request(
            "http://127.0.0.1:8095/api/tickets",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(post_req, timeout=5) as resp:
            res = json.loads(resp.read().decode())
            logger.info(f"⚡ AUTO-INGESTED MISSING TICKET: {ticket_id} -> {res.get('status')}")
    except Exception as e:
        logger.error(f"Failed to auto-ingest ticket {ticket_id}: {e}")


def is_unresolved_task(task_text: str) -> bool:
    if not task_text or not task_text.strip():
        return False
    lines = [l.strip() for l in task_text.strip().splitlines() if l.strip()]
    if not lines:
        return False

    header = lines[0].upper()
    # Skip summary / ledger headers
    if any(ignore in header for ignore in ["RECENTLY RESOLVED", "LEDGER OF RECORD", "HISTORICAL"]):
        return False

    # Check if header explicitly marks it pending / open
    if any(pending in header for pending in ["[PENDING]", "[ACTIVE]", "[IN PROGRESS]", "[OPEN]"]):
        return True

    # If header itself marks it resolved or closed, it's done
    if any(done in header for done in ["[RESOLVED", "RESOLVED & VERIFIED", "[CLOSED"]):
        return False

    # Check top metadata / ticket line (lines 1 to 4)
    for line in lines[1:5]:
        lu = line.upper()
        if any(pending in lu for pending in ["STATE = 1", "[PENDING]", "STATE = 2", "[IN PROGRESS]"]):
            return True
        if any(done in lu for done in ["STATE = 4", "STATE = 5", "[RESOLVED", "[CLOSED"]):
            return False

    # Must have a real task or ticket identifier
    if not re.search(r'\b(TASK\s*\d+|(?:WO|STRY|DFCT|ENHC|REQ|INC|PRB|CHG)\d+)\b', task_text.upper()):
        return False
    return True


def check_unresolved_tasks(content: str) -> list:
    """Extract tasks under active queue that do not contain resolved markers."""
    unresolved = []
    lines = content.splitlines()
    in_next_up = False
    current_task = []

    for line in lines:
        if any(h in line for h in ["## 🎯 NEXT UP FOR CLIO EXECUTION", "## 🎯 ACTIVE RUNNER QUEUE", "## 🎯 NEXT UP", "## 🎯 ACTIVE SPRINT QUEUE"]):
            in_next_up = True
            continue
        elif in_next_up and line.startswith("## ") and not any(h in line for h in ["## 🎯 NEXT UP", "## 🎯 ACTIVE"]):
            in_next_up = False
            if current_task:
                task_text = "\n".join(current_task).strip()
                if is_unresolved_task(task_text):
                    ensure_ticket_registered(task_text)
                    unresolved.append(task_text)
                current_task = []
            break

        if in_next_up:
            if line.startswith("### "):
                if current_task:
                    task_text = "\n".join(current_task).strip()
                    if is_unresolved_task(task_text):
                        ensure_ticket_registered(task_text)
                        unresolved.append(task_text)
                    current_task = []
                current_task.append(line)
            elif current_task:
                current_task.append(line)

    if current_task:
        task_text = "\n".join(current_task).strip()
        if is_unresolved_task(task_text):
            ensure_ticket_registered(task_text)
            unresolved.append(task_text)

    return unresolved


def poll(interval_sec: float = 2.0, exit_on_detect: bool = True, timeout_sec: float = 0.0):
    logger.info("=" * 70)
    logger.info("⚡ SOVEREIGN SCRATCHPAD & PILOT DROPS POLLER ACTIVATED")
    logger.info(f"Target Scratchpad : {SCRATCH_PAD_PATH}")
    logger.info(f"Target Dropzone   : {PILOT_DROPS_DIR}")
    logger.info(f"Poll Interval     : {interval_sec}s")
    logger.info(f"Exit on Detect    : {exit_on_detect}")
    logger.info("=" * 70)

    initial_pad_hash = compute_hash(SCRATCH_PAD_PATH)
    initial_pad_content = read_content(SCRATCH_PAD_PATH)
    initial_files = get_known_files(PILOT_DROPS_DIR)

    # Check if there are already pending unresolved tasks
    existing_unresolved = check_unresolved_tasks(initial_pad_content)
    if existing_unresolved:
        logger.info(f"⚡ Found {len(existing_unresolved)} pending unresolved task(s) on launch!")
        for idx, task in enumerate(existing_unresolved, 1):
            logger.info(f"\n--- PENDING ORDER #{idx} ---\n{task}\n-----------------------")
        if exit_on_detect:
            logger.info("Exiting immediately to process pending order.")
            sys.exit(0)

    logger.info(f"Baseline established. Scratchpad SHA256: {initial_pad_hash[:16]}... (0 pending orders).")
    logger.info("Standing by in Phase 2 Autonomous Dispatch mode. Listening for Pilot drops...")

    start_time = time.time()
    poll_counter = 0

    while True:
        try:
            poll_counter += 1
            if timeout_sec > 0 and (time.time() - start_time) > timeout_sec:
                logger.info(f"Poller reached timeout of {timeout_sec}s with zero new drops.")
                sys.exit(0)

            # 1. Check scratch_pad.md
            current_pad_hash = compute_hash(SCRATCH_PAD_PATH)

            # Emit atomic heartbeat for Poller HUD (WO0010108)
            try:
                import datetime as _dt
                hb_path = Path("/home/james/stacklabs/logs/scratch_pad_poller_heartbeat.json")
                hb_tmp = Path("/home/james/stacklabs/logs/scratch_pad_poller_heartbeat.json.tmp")
                unresolved = check_unresolved_tasks(read_content(SCRATCH_PAD_PATH))
                hb_data = {
                    "timestamp": time.time(),
                    "iso_time": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                    "pid": os.getpid(),
                    "poll_count": poll_counter,
                    "scratch_pad_sha256": current_pad_hash[:16] if current_pad_hash else "",
                    "unresolved_tasks_count": len(unresolved),
                    "status": "LISTENING" if not unresolved else "CLAIMED"
                }
                with open(hb_tmp, "w", encoding="utf-8") as f:
                    json.dump(hb_data, f)
                os.replace(hb_tmp, hb_path)
            except Exception:
                pass

            if current_pad_hash and current_pad_hash != initial_pad_hash:
                current_pad_content = read_content(SCRATCH_PAD_PATH)
                logger.info("🚨 INCOMING CHANGE DETECTED ON SCRATCH_PAD.MD!")

                # Compute diff
                diff_lines = list(
                    difflib.unified_diff(
                        initial_pad_content.splitlines(keepends=True),
                        current_pad_content.splitlines(keepends=True),
                        fromfile="scratch_pad_baseline",
                        tofile="scratch_pad_updated",
                        n=3,
                    )
                )

                unresolved_tasks = check_unresolved_tasks(current_pad_content)
                if unresolved_tasks:
                    logger.info(f"🎯 NEW WORK ORDER(S) CLAIMED ({len(unresolved_tasks)} active):")
                    for idx, t in enumerate(unresolved_tasks, 1):
                        print(f"\n=======================================================")
                        print(f"📥 INCOMING ORDER #{idx} READY FOR CLIO EXECUTION:")
                        print(f"=======================================================")
                        print(t)
                        print(f"=======================================================\n")
                else:
                    print("\n=======================================================")
                    print("📝 SCRATCHPAD MODIFIED (DIFF DETECTED):")
                    print("=======================================================")
                    print("".join(diff_lines[:40]))
                    print("=======================================================\n")

                if exit_on_detect:
                    logger.info("Terminating poller successfully with detected order.")
                    sys.exit(0)
                else:
                    initial_pad_hash = current_pad_hash
                    initial_pad_content = current_pad_content

            # 2. Check for newly dropped files in pilot_drops
            current_files = get_known_files(PILOT_DROPS_DIR)
            for fpath, mtime in current_files.items():
                if fpath not in initial_files or mtime > initial_files.get(fpath, 0):
                    p = Path(fpath)
                    logger.info(f"🚨 NEW PILOT DROP FILE DETECTED: {p.name}")
                    content = read_content(p)
                    print(f"\n=======================================================")
                    print(f"📥 NEW WORK ORDER FILE DROPPED: {p.name}")
                    print(f"=======================================================")
                    print(content[:2000])
                    if len(content) > 2000:
                        print(f"\n... [Truncated {len(content) - 2000} bytes] ...")
                    print(f"=======================================================\n")

                    if exit_on_detect:
                        logger.info("Terminating poller successfully with detected drop file.")
                        sys.exit(0)
                    else:
                        initial_files = current_files

        except Exception as e:
            logger.error(f"Error in poller loop: {e}")

        time.sleep(interval_sec)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sovereign Scratchpad & Pilot Drops Poller")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds (default: 2.0)")
    parser.add_argument("--loop", action="store_true", help="Run indefinitely in a loop without exiting on detect")
    parser.add_argument("--timeout", type=float, default=0.0, help="Optional timeout in seconds (0 = infinite)")
    args = parser.parse_args()

    poll(interval_sec=args.interval, exit_on_detect=not args.loop, timeout_sec=args.timeout)
