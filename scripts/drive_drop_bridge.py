#!/usr/bin/env python3
"""
Sovereign OS — Autonomous Google Drive Drop Bridge
System Specification: SL-SPEC-2026-DRIVE-BRIDGE-001 / Tool #50
Node: Clio (clio.stacklabs.internal)
Path: /home/james/stacklabs/scripts/drive_drop_bridge.py

Mandate:
Monitors remote Google Drive inboxes (stacklabs_edge:01_Pilot_Drive_Inbox/ and fallback stacklabs_vault:01_Pilot_Drive_Inbox/).
When documents (.md, .docx, .txt, .pdf) are dropped by the Pilot via mobile Google Drive / Spark:
1. Downloads them to local staging (/home/james/sovereign_inbox/pilot_drops/drive_inbox/).
2. Moves remote files to remote archive (01_Pilot_Drive_Inbox/archive/).
3. Automatically provisions next ticket number via FastAPI / api_client.
4. Drops an atomic work order (WO0010XXX-INGEST-DRIVE-DROP-{clean_slug}.md) into /home/james/sovereign_inbox/queue/incoming/.
5. Updates pilot scratch pad and logs events to /home/james/sovereign_inbox/queue/logs/drive_bridge.log.
"""

import sys
import os
import re
import time
import json
import logging
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure SovereignOS scripts directory is on sys.path
BASE_DIR = Path("/home/james/stacklabs")
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Local Target Directories
LOCAL_INBOX_DIR = Path("/home/james/stacklabs/pilot_drops/drive_inbox")
LOCAL_QUEUE_DIR = Path("/home/james/stacklabs/queue/incoming")
LOCAL_LOG_DIR = Path("/home/james/stacklabs/queue/logs")
LOCAL_LOG_FILE = LOCAL_LOG_DIR / "drive_bridge.log"
SCRATCH_PAD_PATH = Path("/home/james/stacklabs/pilot_drops/scratch_pad.md")

# Remote Drive Paths
REMOTE_INBOXES = [
    "stacklabs_edge:01_Pilot_Drive_Inbox",
    "stacklabs_vault:01_Pilot_Drive_Inbox",
]

# Supported Document Extensions
SUPPORTED_EXTENSIONS = {".docx", ".doc", ".md", ".txt", ".pdf", ".rtf", ".csv", ".json"}

# Logging configuration
LOCAL_LOG_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_INBOX_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_QUEUE_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("DriveDropBridge")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Console handler
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

# File handler
fh = logging.FileHandler(str(LOCAL_LOG_FILE), encoding="utf-8")
fh.setFormatter(formatter)
logger.addHandler(fh)


def sanitize_slug(text: str, max_length: int = 40) -> str:
    """Create a URL/filename-safe clean slug from string."""
    name_no_ext = os.path.splitext(text)[0]
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", name_no_ext).strip("-").lower()
    if not cleaned:
        cleaned = "unnamed-drop"
    return cleaned[:max_length].strip("-")


def get_next_ticket_id(slug: str) -> str:
    """Acquire next hybrid ticket ID via FastAPI or local fallback."""
    try:
        from scripts.core import api_client
        hybrid_id = api_client.get_next_hybrid_number(
            category="WO",
            slug=f"INGEST-DRIVE-DROP-{slug.upper()}",
            increment=True,
        )
        if hybrid_id:
            return hybrid_id
    except Exception as e:
        logger.warning(f"Could not reach FastAPI next_number endpoint ({e}); falling back to local inspection...")

    # Local fallback: inspect queue and tickets
    highest_num = 10298
    for p in LOCAL_QUEUE_DIR.glob("WO*.md"):
        m = re.search(r"WO00(\d{5})", p.name)
        if m:
            num = int(m.group(1))
            if num > highest_num:
                highest_num = num
    next_num = highest_num + 1
    return f"WO00{next_num}-INGEST-DRIVE-DROP-{slug.upper()}"


def register_ticket_in_api(ticket_id: str, title: str, description: str, local_path: Path):
    """Registers ticket in FastAPI portal so SDLC ledger tracks it."""
    try:
        from scripts.core import api_client
        api_client.create_ticket(
            number=ticket_id,
            title=title,
            ticket_type="WorkOrder",
            description=f"[headless] [non-ui] {description}",
            priority="P2",
            status="PLANNING",
            assigned_to="agy",
            affected_ci="50_DriveDropBridge",
            work_notes=f"Ingested by Tool #50 drive_drop_bridge.py. Staged file: {local_path}",
        )
        logger.info(f"Registered SDLC ticket in FastAPI: {ticket_id}")
    except Exception as e:
        logger.warning(f"Could not register SDLC ticket in FastAPI ({e}); work order file staged locally.")


def ensure_remote_inbox(remote: str) -> bool:
    """Ensure remote inbox folder and archive folder exist."""
    try:
        subprocess.run(["rclone", "mkdir", remote], check=True, capture_output=True, text=True, timeout=30)
        subprocess.run(["rclone", "mkdir", f"{remote}/archive"], check=True, capture_output=True, text=True, timeout=30)
        return True
    except Exception as e:
        logger.error(f"Error creating/checking remote directory {remote}: {e}")
        return False


def list_remote_files(remote: str) -> List[str]:
    """List pending files in remote inbox excluding archive directory."""
    try:
        cmd = ["rclone", "lsf", "--files-only", remote]
        res = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
        files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        return [f for f in files if not f.startswith("archive/")]
    except Exception as e:
        logger.warning(f"Failed to list remote files for {remote}: {e}")
        return []


def download_remote_file(remote: str, filename: str) -> Optional[Path]:
    """Download single file from remote to local inbox target."""
    remote_src = f"{remote}/{filename}"
    local_target = LOCAL_INBOX_DIR / filename
    try:
        logger.info(f"Downloading from Google Drive: {remote_src} -> {local_target}")
        cmd = ["rclone", "copy", remote_src, str(LOCAL_INBOX_DIR)]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        if local_target.exists():
            return local_target
        # Check if rclone changed extension during export (e.g. google doc to .docx)
        base = os.path.splitext(filename)[0]
        for candidate in LOCAL_INBOX_DIR.glob(f"{base}*"):
            if candidate.is_file():
                return candidate
    except Exception as e:
        logger.error(f"Failed to download remote file {remote_src}: {e}")
    return None


def archive_remote_file(remote: str, filename: str) -> bool:
    """Move processed file into remote archive folder."""
    remote_src = f"{remote}/{filename}"
    remote_dst = f"{remote}/archive/{filename}"
    try:
        logger.info(f"Archiving on Google Drive: {remote_src} -> {remote_dst}")
        cmd = ["rclone", "moveto", remote_src, remote_dst]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        return True
    except Exception as e:
        logger.error(f"Failed to archive remote file {remote_src}: {e}")
        return False


def generate_work_order(ticket_id: str, filename: str, local_path: Path, remote_src: str) -> Path:
    """Generate canonical atomic work order markdown file for Aggy."""
    wo_path = LOCAL_QUEUE_DIR / f"{ticket_id}.md"
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_title = os.path.splitext(filename)[0].replace("-", " ").replace("_", " ").title()

    content = f"""# ⚡ WORK ORDER: {ticket_id} — INGEST DRIVE DROP: {clean_title}

**Ticket ID:** `{ticket_id}`  
**Parent Epic:** `SOVEREIGN-DRIVE-BRIDGE-TOOL-50`  
**Assigned Worker:** `agy` on Clio (Workstation Engine / Headless Metal Forge)  
**Priority:** `HIGH` (Operational Ingress)  
**Timestamp:** `{now_iso}`  
**Source Path:** `{local_path}`  
**Origin Remote:** `{remote_src}`  

---

## 🏛️ Scope of Work & Mandate
1. **Document Intake**: Read and ingest the newly dropped Google Drive document:
   [`{local_path.name}`](file://{local_path.resolve()}).
2. **Insight Extraction**: Extract all core strategic insights, architecture specifications, operator instructions, financial figures, or battle plans.
3. **Artifact Staging**: If appropriate, stage distilled canonical documents into:
   - Permanent Docs: `/home/james/stacklabs/dna/docs/`
   - Weekly Sync Dropzone: `/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/`
4. **Scratch Pad Update**: Update the active Pilot scratch pad at `/home/james/sovereign_inbox/pilot_drops/scratch_pad.md`.
5. **Execution**: Execute any actionable requests or deliverables specified within the document.
6. **SDLC Resolution**: Auto-resolve the ticket via FastAPI (`http://127.0.0.1:8095/api/tickets/{ticket_id}`) and move this work order to `/home/james/sovereign_inbox/queue/archive/`.
"""
    wo_path.write_text(content, encoding="utf-8")
    logger.info(f"Staged atomic work order: {wo_path}")
    return wo_path


def update_scratch_pad(ticket_id: str, filename: str, local_path: Path):
    """Appends intake notification to Pilot scratch pad."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n- **[{now_str}] 📥 GOOGLE DRIVE DROP**: Ingested `{filename}` -> Staged work order `{ticket_id}` ([`{local_path.name}`](file://{local_path.resolve()}))\n"
    try:
        if SCRATCH_PAD_PATH.exists():
            with open(SCRATCH_PAD_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
        else:
            SCRATCH_PAD_PATH.write_text(f"# ⚡ PILOT SCRATCH PAD\n{entry}", encoding="utf-8")
        logger.info(f"Updated scratch pad at {SCRATCH_PAD_PATH}")
    except Exception as e:
        logger.warning(f"Could not update scratch pad: {e}")


def process_file(file_path: Path) -> bool:
    """Check if file is a Spark Crucible Proposal and ingest into database."""
    if file_path.name.startswith("SPARK_CRUCIBLE_PROPOSAL_") and file_path.suffix == ".md":
        m = re.search(r"SPARK_CRUCIBLE_PROPOSAL_(CHAL-[A-Z0-9-]+)\.md", file_path.name)
        if m:
            sys_id = m.group(1)
            logger.info(f"🦄 [UNICORN UAT] Detected Spark Crucible Proposal for {sys_id}: {file_path.name}")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    proposal_content = f.read()

                # Update sys_approval_queue in sovereign_now.db
                from core.db import get_db
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE sys_approval_queue
                        SET state = 'Crucible_Proposal_Ready',
                            plan_markdown = ?,
                            comments = 'Spark proposal ingested from Google Drive',
                            sys_updated_on = CURRENT_TIMESTAMP
                        WHERE sys_id = ?
                    """, (proposal_content, sys_id))
                    conn.commit()
                logger.info(f"✅ Successfully updated {sys_id} to Crucible_Proposal_Ready with Spark proposal.")

                # Move remote proposal to archive on Drive
                for remote in REMOTE_INBOXES:
                    subprocess.run([
                        "rclone", "moveto",
                        f"{remote}/{file_path.name}",
                        f"{remote}/archive/{file_path.name}"
                    ], capture_output=True, timeout=15)

                return True
            except Exception as e:
                logger.error(f"Failed to ingest Spark proposal {file_path.name}: {e}")
                return False
    return False


def scan_and_ingest_inbox(remote: str) -> List[Dict[str, Any]]:
    """Scan single remote inbox, process files, and generate work orders."""
    ensure_remote_inbox(remote)
    files = list_remote_files(remote)
    if not files:
        return []

    processed = []
    for fname in files:
        # Skip outbound requests so they stay on Drive for Spark scheduler
        if fname.startswith("SPARK_CRUCIBLE_REQUEST_"):
            logger.info(f"Skipping outbound Spark Crucible Request: {fname}")
            continue

        ext = os.path.splitext(fname)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS and not ext == "":
            logger.info(f"Skipping unsupported file extension: {fname}")
            continue

        logger.info(f"Processing Google Drive drop: {fname} from {remote}")
        local_file = download_remote_file(remote, fname)
        if not local_file:
            continue

        # Check if file is a Spark Crucible Proposal
        if fname.startswith("SPARK_CRUCIBLE_PROPOSAL_"):
            if process_file(local_file):
                processed.append({
                    "filename": fname,
                    "local_path": str(local_file),
                    "type": "SPARK_CRUCIBLE_PROPOSAL",
                    "remote": remote
                })
            continue

        slug = sanitize_slug(fname)
        ticket_id = get_next_ticket_id(slug)
        title = f"Ingest Drive Drop: {fname}"
        description = f"Autonomous Google Drive Drop Ingestion for {fname} from {remote}."

        register_ticket_in_api(ticket_id, title, description, local_file)
        wo_path = generate_work_order(ticket_id, fname, local_file, f"{remote}/{fname}")
        update_scratch_pad(ticket_id, fname, local_file)
        archive_remote_file(remote, fname)

        processed.append({
            "ticket_id": ticket_id,
            "filename": fname,
            "local_path": str(local_file),
            "work_order": str(wo_path),
            "remote": remote,
        })
    return processed


def run_poll_cycle() -> List[Dict[str, Any]]:
    """Execute complete poll cycle across primary and fallback remotes."""
    all_processed = []
    logger.info("⚡ Executing Google Drive Drop Bridge poll cycle...")

    for remote in REMOTE_INBOXES:
        results = scan_and_ingest_inbox(remote)
        all_processed.extend(results)

    logger.info(f"Poll cycle complete. Ingested {len(all_processed)} documents.")
    return all_processed


def main():
    parser = argparse.ArgumentParser(description="Autonomous Google Drive Drop Bridge for Sovereign OS")
    parser.add_argument("--once", "--run-once", dest="once", action="store_true", help="Run a single poll cycle and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background daemon loop")
    parser.add_argument("--interval", type=int, default=60, help="Poll interval in seconds for daemon mode (default 60s)")
    args = parser.parse_args()

    if args.daemon:
        logger.info(f"Starting Google Drive Drop Bridge Daemon (Interval: {args.interval}s)...")
        while True:
            try:
                run_poll_cycle()
            except Exception as e:
                logger.error(f"Error during poll cycle: {e}", exc_info=True)
            time.sleep(args.interval)
    else:
        # Default or --once / --run-once
        results = run_poll_cycle()
        print(json.dumps({"status": "success", "ingested_count": len(results), "items": results}, indent=2))


if __name__ == "__main__":
    main()
