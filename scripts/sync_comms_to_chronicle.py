#!/usr/bin/env python3
"""
scripts/sync_comms_to_chronicle.py — Unified Communications Sync Engine & Chronicle Compiler
=============================================================================================
System: Clio Host (StackLabs Ingress Pipeline)
Authoritative Ticket: WO0010502-SMS-EMAIL-CHRONICLE-SYNC-WORKFLOW

Ingests communications from dual sources:
1. Android SMS/MMS/RCS backups from Google Drive (stacklabs_edge:sms_backup/)
2. Corporate Google Workspace IMAP (james@stacklabsllc.com)

Compiles un-synced correspondence directly into:
- Canonical Counterparty Ledgers:
  * Pawel Rudnicki: dna/docs/13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md [LOG-PR-XXX]
  * Jeremy Malone: 06_Davidson_Malone_Prospectus/... [LOG-JM-XXX]
  * Jeff U'Ren: 11_JeffUren_Prospectus/... [LOG-JU-XXX]
- Latest Daily Session Report: stacklabs_inbox/today/SESSION_REPORT_*.md
- Weekly Master Chronicles: StackLabs_Internal/epoch_sources/SESSION_CHRONICLE_CURRENT_WEEK.md
"""

import os
import sys
import re
import time
import glob
import fcntl
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.db import get_db
import scripts.sms_backup_parser as sms_parser
import scripts.sync_canonical_communications as email_sync

# Setup Logging
LOG_FILE = Path("/home/james/stacklabs_inbox/logs/sync_comms_to_chronicle.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SyncCommsChronicle")

# Canonical Ledgers & Chronicles
PAWEL_LEDGER = Path("/home/james/stacklabs/dna/docs/13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md")
PAWEL_GOV_LEDGER = Path("/home/james/stacklabs/config/governance/13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md")
PAWEL_NOTEBOOK_LEDGER = Path("/home/james/stacklabs_inbox/notebook_sync/03_WildSeed_\x53overeign_Swarm/13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md")
JEREMY_LEDGER = Path("/home/james/stacklabs_inbox/notebook_sync/06_Davidson_Malone_Prospectus/01_CANONICAL_COMMUNICATIONS_LOG_AND_OPERATOR_DOSSIER_JEREMY_MALONE.md")
JEFF_LEDGER = Path("/home/james/stacklabs_inbox/notebook_sync/11_JeffUren_Prospectus/01_CANONICAL_COMMUNICATIONS_LOG_AND_OPERATOR_DOSSIER_JEFF_UREN.md")

CHRONICLE_PATHS = [
    Path("/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/epoch_sources/SESSION_CHRONICLE_CURRENT_WEEK.md"),
    Path("/home/james/stacklabs/StackLabs_Internal/epoch_sources/SESSION_CHRONICLE_CURRENT_WEEK.md"),
]
SYNC_GDRIVE_SCRIPT = Path("/home/james/stacklabs/scripts/sync_to_gdrive.sh")
TODAY_DIR = Path("/home/james/stacklabs_inbox/today")


def clean_body_text(body: Optional[str]) -> str:
    """Strips <smil> tags, null markers, and leading/trailing whitespace."""
    if not body:
        return ""
    # Remove XML SMIL tags from MMS
    cleaned = re.sub(r'<smil>.*?</smil>\s*', '', body, flags=re.DOTALL)
    cleaned = cleaned.strip()
    return cleaned


def format_readable_time(timestamp_ny: str) -> str:
    """Converts 'YYYY-MM-DD HH:MM:SS EDT' to 'Month Day, Year (HH:MM EDT)'."""
    try:
        parts = timestamp_ny.strip().split()
        if len(parts) >= 2:
            dt = datetime.strptime(f"{parts[0]} {parts[1]}", "%Y-%m-%d %H:%M:%S")
            tz = parts[2] if len(parts) > 2 else "EDT"
            return f"{dt.strftime('%B %-d, %Y')} ({dt.strftime('%H:%M')} {tz})"
    except Exception:
        pass
    return timestamp_ny


def get_latest_session_report() -> Optional[Path]:
    """Resolves the most recent daily session report."""
    candidates = sorted(TODAY_DIR.glob("SESSION_REPORT_20*.md"))
    if not candidates:
        candidates = sorted(TODAY_DIR.glob("SESSION_REPORT_*.md"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def get_next_sequence_number(file_path: Path, prefix: str) -> int:
    """Scans ledger file to extract the highest [PREFIX-XXX] sequence number."""
    max_num = 0
    pattern = re.compile(rf'\[?{prefix}-(\d+)\]?')
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    for match in pattern.finditer(line):
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num
        except Exception as e:
            logger.warning(f"Error scanning sequence numbers in {file_path}: {e}")
    return max_num + 1


def append_with_lock(target_path: Path, content: str, dry_run: bool = False) -> bool:
    """Atomically appends content to target file using fcntl flock."""
    if dry_run:
        logger.info(f"[DRY-RUN] Would append to {target_path} ({len(content)} chars)")
        return True

    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(target_path, "a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(content)
            fcntl.flock(f, fcntl.LOCK_UN)
        logger.info(f"Appended entry to {target_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to append to {target_path}: {e}")
        return False


def sync_emails(dry_run: bool = False) -> int:
    """Polls Google Workspace IMAP for partner correspondence."""
    logger.info("Starting email ingress sync via sync_canonical_communications...")
    try:
        count = email_sync.run_sync_cycle(dry_run=dry_run)
        logger.info(f"Email sync finished. {count} new email(s) ingested.")
        return count
    except Exception as e:
        logger.error(f"Error during email sync: {e}")
        return 0


def sync_sms_and_calls(dry_run: bool = False) -> int:
    """Pulls newest XML backups from Google Drive and parses into SQLite."""
    logger.info("Starting SMS & call backup ingress via sms_backup_parser...")
    try:
        results = sms_parser.run_pipeline(sync=not dry_run, parse=True)
        new_records = (
            results.get("sms_new", 0)
            + results.get("calls_new", 0)
            + results.get("compiled_to_chronicle", 0)
        )
        logger.info(f"SMS/Call sync finished. {new_records} record(s) processed.")
        return new_records
    except Exception as e:
        logger.error(f"Error during SMS/Call backup sync: {e}")
        return 0


def compile_unlogged_sms(dry_run: bool = False) -> int:
    """
    Queries phone_sms_ingress where synced_to_ledger = 0, formats entries,
    appends to canonical counterparty ledgers, session reports, and weekly chronicles,
    and updates synced_to_ledger = 1 in SQLite.
    """
    logger.info("Checking for un-synced SMS/RCS messages in phone_sms_ingress...")

    with get_db(row_factory=False) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, message_type, address, contact_name, date_epoch, timestamp_ny,
                   body, read_status, is_sent, counterparty, source_file
            FROM phone_sms_ingress
            WHERE synced_to_ledger = 0
            ORDER BY date_epoch ASC;
        """)
        rows = cursor.fetchall()

    if not rows:
        logger.info("Zero un-synced SMS messages found.")
        return 0

    logger.info(f"Found {len(rows)} un-synced SMS record(s). Starting compilation...")

    # Load initial sequence counters
    pr_num = get_next_sequence_number(PAWEL_LEDGER, "LOG-PR")
    jm_num = get_next_sequence_number(JEREMY_LEDGER, "LOG-JM")
    ju_num = get_next_sequence_number(JEFF_LEDGER, "LOG-JU")

    latest_report = get_latest_session_report()
    processed_ids = []
    compiled_count = 0

    for row in rows:
        (row_id, msg_type, address, contact_name, date_epoch, timestamp_ny,
         raw_body, read_status, is_sent, counterparty, source_file) = row

        clean_body = clean_body_text(raw_body)
        direction = "OUTBOUND" if is_sent else "INBOUND"

        # If body is completely empty or just '[Media: null]' / '[MMS Media / No Text]', mark as synced without adding blank entry
        if not clean_body or clean_body in ("[Media: null]", "[MMS Media / No Text]"):
            processed_ids.append(row_id)
            continue

        if is_sent:
            sender = "James Carroll (Pilot)"
            recipient_label = counterparty or contact_name or address or "External Contact"
            recipient = f"{recipient_label} ({address})" if address else recipient_label
        else:
            sender_label = counterparty or contact_name or address or "External Contact"
            sender = f"{sender_label} ({address})" if address else sender_label
            recipient = "James Carroll (Pilot)"

        readable_date = format_readable_time(timestamp_ny)

        # 1. Compile into Specific Counterparty Ledgers
        if counterparty == "Pawel Rudnicki":
            tag = f"[LOG-PR-{pr_num:03d}]"
            pr_num += 1
            entry = f"""
---

### {tag} {readable_date} — {direction} SMS / RCS
* **Direction:** {direction} (Mobile SMS / RCS)
* **Sender:** {sender}
* **Recipient:** {recipient}
* **Timestamp:** {timestamp_ny}
* **Channel:** Mobile SMS / RCS Ingress (Phone Backup)

```text
{clean_body}
```
"""
            append_with_lock(PAWEL_LEDGER, entry, dry_run=dry_run)
            append_with_lock(PAWEL_GOV_LEDGER, entry, dry_run=dry_run)
            append_with_lock(PAWEL_NOTEBOOK_LEDGER, entry, dry_run=dry_run)

        elif counterparty == "Jeremy Malone":
            tag = f"[LOG-JM-{jm_num:03d}]"
            jm_num += 1
            entry = f"""
---

### {tag} {readable_date} — {direction} SMS
* **Direction:** {direction} (Mobile SMS / RCS)
* **Sender:** {sender}
* **Recipient:** {recipient}
* **Timestamp:** {timestamp_ny}
* **Channel:** Mobile SMS / RCS Ingress (Phone Backup)

```text
{clean_body}
```
"""
            append_with_lock(JEREMY_LEDGER, entry, dry_run=dry_run)

        elif counterparty == "Jeff U'Ren":
            tag = f"[LOG-JU-{ju_num:03d}]"
            ju_num += 1
            entry = f"""
---

### {tag} {readable_date} — {direction} SMS
* **Direction:** {direction} (Mobile SMS / RCS)
* **Sender:** {sender}
* **Recipient:** {recipient}
* **Timestamp:** {timestamp_ny}
* **Channel:** Mobile SMS / RCS Ingress (Phone Backup)

```text
{clean_body}
```
"""
            append_with_lock(JEFF_LEDGER, entry, dry_run=dry_run)

        # 2. Compile into Weekly Master Chronicles & Daily Session Report
        target_name = counterparty or contact_name or address or "External Contact"
        chronicle_entry = f"""
---

### [{direction} SMS] {target_name}
* **Timestamp:** {timestamp_ny}
* **From:** `{sender}`
* **To:** `{recipient}`
* **Entity:** {counterparty or "External Contact"}
* **Channel:** Mobile SMS / RCS Ingress (Phone Backup)

```text
{clean_body}
```
"""
        # Append to Daily Session Report
        if latest_report and latest_report.exists():
            append_with_lock(latest_report, chronicle_entry, dry_run=dry_run)

        # Append to Weekly Chronicles
        for c_path in CHRONICLE_PATHS:
            if c_path.exists():
                append_with_lock(c_path, chronicle_entry, dry_run=dry_run)

        processed_ids.append(row_id)
        compiled_count += 1

    # Mark rows as synced in SQLite
    if not dry_run and processed_ids:
        with get_db(row_factory=False) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.executemany(
                "UPDATE phone_sms_ingress SET synced_to_ledger = 1 WHERE id = ?;",
                [(pid,) for pid in processed_ids]
            )
            conn.commit()
        logger.info(f"Marked {len(processed_ids)} SMS records as synced_to_ledger = 1 in SQLite.")

    return compiled_count


def show_latest_comms(limit: int = 5):
    """Prints a formatted terminal briefing of latest correspondence."""
    print("\n" + "=" * 80)
    print("📡 STACKLABS COMMUNICATIONS RADAR — LATEST CORRESPONDENCE")
    print("=" * 80)

    # 1. Latest SMS / RCS Messages
    print(f"\n📱 LATEST MOBILE SMS / RCS MESSAGES (Limit: {limit}):")
    try:
        with get_db(row_factory=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp_ny, is_sent, counterparty, contact_name, address, body
                FROM phone_sms_ingress
                ORDER BY date_epoch DESC
                LIMIT ?;
            """, (limit,))
            sms_rows = cursor.fetchall()

        if not sms_rows:
            print("  (No SMS records found in phone_sms_ingress)")
        else:
            for r in sms_rows:
                ts, is_sent, cp, contact, addr, raw_body = r
                direction = "OUTBOUND ->" if is_sent else "INBOUND <-"
                party = cp or contact or addr or "Unknown"
                clean = clean_body_text(raw_body).replace("\n", " ")
                snippet = clean[:90] + ("..." if len(clean) > 90 else "")
                print(f"  • [{ts}] {direction} {party} ({addr}):")
                print(f"    \"{snippet}\"")
    except Exception as e:
        print(f"  [!] Error querying SMS: {e}")

    # 2. Latest Emails from Ledgers/State
    print(f"\n📧 LATEST CORPORATE EMAILS (james@stacklabsllc.com):")
    try:
        if PAWEL_LEDGER.exists():
            with open(PAWEL_LEDGER, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            email_matches = re.findall(
                r'### \[(?:INBOUND|OUTBOUND) EMAIL\] ([^\n]+)\n\* \*\*Timestamp:\*\* ([^\n]+)\n\* \*\*From:\*\* `([^`]+)`\n\* \*\*To:\*\* `([^`]+)`',
                content
            )
            if email_matches:
                for subj, ts, sender, to_addr in email_matches[-limit:]:
                    dir_str = "OUTBOUND ->" if "james@stacklabsllc.com" in sender.lower() else "INBOUND <-"
                    print(f"  • [{ts}] {dir_str} {subj}")
                    print(f"    From: {sender} | To: {to_addr}")
            else:
                print("  (No email entries logged in partner ledgers)")
        else:
            print("  (Partner ledger not found)")
    except Exception as e:
        print(f"  [!] Error querying emails: {e}")

    print("\n" + "=" * 80 + "\n")


def run_full_sync_and_compile(dry_run: bool = False) -> int:
    """Executes full sync and compile pass."""
    logger.info("Executing Full Unified Communications Sync Pass...")
    t0 = time.time()

    email_count = sync_emails(dry_run=dry_run)
    sms_count = sync_sms_and_calls(dry_run=dry_run)
    compiled_sms = compile_unlogged_sms(dry_run=dry_run)

    total_changes = email_count + sms_count + compiled_sms
    logger.info(
        f"Sync pass completed in {time.time() - t0:.2f}s: "
        f"{email_count} new email(s), {sms_count} new backup record(s), {compiled_sms} SMS compiled to chronicles."
    )

    # Ensure FTS5 search index is fully synchronized
    try:
        from scripts.comms_indexer import run_indexing
        logger.info("Synchronizing SQLite FTS5 comms search index...")
        run_indexing()
    except Exception as e:
        logger.warning(f"Error during comms indexing in chronicle sync: {e}")

    if total_changes > 0 and not dry_run and SYNC_GDRIVE_SCRIPT.exists():
        logger.info("Triggering Google Drive replication script sync_to_gdrive.sh...")
        try:
            subprocess.run(["/bin/bash", str(SYNC_GDRIVE_SCRIPT)], check=False)
            logger.info("Google Drive replication triggered cleanly.")
        except Exception as e:
            logger.warning(f"Error triggering sync_to_gdrive.sh: {e}")

    return total_changes


def main():
    parser = argparse.ArgumentParser(
        description="Unified Communications Sync Engine & Chronicle Compiler (SMS/MMS + Google Workspace IMAP)"
    )
    parser.add_argument(
        "--sync-and-compile",
        action="store_true",
        help="Execute full ingress sync and compile un-synced comms into ledgers and chronicles"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Inspect and display latest correspondence without mutating ledgers or chronicles"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of recent records to display (default: 5)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without modifying files or updating SQLite flags"
    )

    args = parser.parse_args()

    if args.check_only:
        show_latest_comms(limit=args.limit)
        return

    if args.sync_and_compile:
        run_full_sync_and_compile(dry_run=args.dry_run)
        show_latest_comms(limit=args.limit)
        return

    # Default action if no arguments provided: run full sync and compile
    run_full_sync_and_compile(dry_run=args.dry_run)
    show_latest_comms(limit=args.limit)


if __name__ == "__main__":
    main()
