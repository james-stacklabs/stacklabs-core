#!/usr/bin/env python3
"""
scripts/sms_backup_parser.py — Hourly SMS, RCS, & Call Log Ingress Pipeline
===========================================================================
System: Clio Host (StackLabs Ingress Pipeline)
Authoritative Ticket: WO0010499-HOURLY-SMS-BACKUP-INGRESS-AND-XML-PARSER-CRON

Syncs Google Drive backups from `stacklabs_edge:sms_backup/` to 
`/home/james/stacklabs_inbox/today/sms_backup/` and parses Android SMS/MMS/RCS 
XML logs directly into `dna/sovereign_now.db` table `phone_sms_ingress`.
"""

import os
import sys
import glob
import time
import re
import zoneinfo
import logging
import argparse
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.db import get_db

# Paths & Configuration
DRIVE_REMOTE = "stacklabs_edge:sms_backup/"
LOCAL_SYNC_DIR = Path("/home/james/stacklabs_inbox/today/sms_backup")
LOG_FILE = Path("/home/james/stacklabs/logs/sms_backup_ingress.log")
DB_PATH = Path("/home/james/stacklabs/dna/sovereign_now.db")

# Setup Logging
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SMS_Backup_Parser")


def init_db(db_path: Path = DB_PATH):
    """Ensure required database schema and indexes exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_db(row_factory=False) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS phone_sms_ingress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_type TEXT NOT NULL,
                address TEXT,
                contact_name TEXT,
                date_epoch INTEGER NOT NULL,
                timestamp_ny TEXT NOT NULL,
                body TEXT,
                read_status INTEGER DEFAULT 1,
                is_sent INTEGER DEFAULT 0,
                counterparty TEXT,
                source_file TEXT,
                synced_to_ledger INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_phone_sms_ingress_dedupe 
            ON phone_sms_ingress (date_epoch, address, body);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_phone_sms_ingress_counterparty 
            ON phone_sms_ingress (counterparty);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_phone_sms_ingress_date 
            ON phone_sms_ingress (date_epoch);
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS phone_calls_ingress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT,
                contact_name TEXT,
                date_epoch INTEGER NOT NULL,
                timestamp_ny TEXT NOT NULL,
                duration INTEGER DEFAULT 0,
                call_type INTEGER,
                readable_date TEXT,
                counterparty TEXT,
                source_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_phone_calls_ingress_dedupe 
            ON phone_calls_ingress (date_epoch, number, call_type);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_phone_calls_ingress_counterparty 
            ON phone_calls_ingress (counterparty);
        """)
        conn.commit()


COUNTERPARTY_RULES: List[Tuple[str, List[str]]] = [
    ("Pawel Rudnicki", ["2146731978", "pawel", "rudnicki"]),
    ("Jeremy Malone", ["6155172866", "jeremy", "malone", "davidson"]),
    ("Jeff Schroeder", ["jeff schroeder", "schroeder", "vaporware"]),
    ("Jeff U'Ren", ["9015964278", "4045550188", "j unit", "jeff uren", "u'ren", "jeff"]),
    ("Cherylyn", ["cherlyn", "cherylyn"]),
    ("Barb", ["7707332364", "barb", "barbara"]),
    ("Nick", ["nick", "nicholas"]),
    ("Lisa Calhoun", ["lisa calhoun", "valor"]),
    ("Stephen Emery", ["stephen emery", "steve emery"]),
    ("Eileen Carroll", ["9015818188", "eileen"]),
]


def _matches_token(token: str, text: str) -> bool:
    if not token or not text:
        return False
    if token.isdigit() or " " in token or "'" in token or "-" in token:
        return token in text
    return bool(re.search(rf"\b{re.escape(token)}\b", text))


def resolve_counterparty(contact_name: Optional[str], address: Optional[str], body: Optional[str] = "") -> Optional[str]:
    """Identify key counterparties and contacts across names, numbers, and text bodies."""
    addr = (address or "").lower()
    name = (contact_name or "").lower()

    # 1. Check contact_name and address first
    target = f"{name} {addr}".strip()
    for cp_name, tokens in COUNTERPARTY_RULES:
        for t in tokens:
            if _matches_token(t, target):
                return cp_name

    # 2. Check body only if no direct contact name/address was recognized
    if body:
        b_lower = body.lower()
        for cp_name, tokens in COUNTERPARTY_RULES:
            for t in tokens:
                if _matches_token(t, b_lower):
                    return cp_name

    return None


def sync_drive_backups() -> bool:
    """Sync backup XML files from Google Drive using rclone."""
    LOCAL_SYNC_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "rclone", "copy", "--update",
        DRIVE_REMOTE, str(LOCAL_SYNC_DIR)
    ]
    logger.info(f"Starting rclone sync from {DRIVE_REMOTE} to {LOCAL_SYNC_DIR}...")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"rclone sync completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"rclone sync failed: {e.stderr.strip() if e.stderr else e}")
        return False
    except FileNotFoundError:
        logger.error("rclone executable not found on host.")
        return False


def _epoch_to_ny_timestamp(date_epoch: int, fallback: str = "") -> str:
    """Convert millisecond epoch timestamp to Eastern Time string."""
    try:
        epoch_sec = date_epoch / 1000.0 if date_epoch > 10**11 else float(date_epoch)
        eastern = zoneinfo.ZoneInfo("America/New_York")
        return datetime.fromtimestamp(epoch_sec, tz=eastern).strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return fallback or datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_sms_xml(xml_path: Path, db_path: Path = DB_PATH) -> Tuple[int, int, Dict[str, int]]:
    """
    Stream-parse SMS and MMS/RCS XML backup file into SQLite table phone_sms_ingress.
    Returns: (total_parsed, new_inserted, partner_counts)
    """
    total_parsed = 0
    new_inserted = 0
    partner_counts: Dict[str, int] = {}
    batch = []
    batch_size = 500
    source_filename = xml_path.name

    logger.info(f"Parsing SMS/MMS XML: {xml_path}...")
    t0 = time.time()

    with get_db(row_factory=False) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()

        def flush_batch():
            nonlocal new_inserted
            if not batch:
                return
            inserted_before = conn.total_changes
            cursor.executemany("""
                INSERT OR IGNORE INTO phone_sms_ingress (
                    message_type, address, contact_name, date_epoch, timestamp_ny,
                    body, read_status, is_sent, counterparty, source_file, synced_to_ledger
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, batch)
            conn.commit()
            new_inserted += (conn.total_changes - inserted_before)
            batch.clear()

        for event, elem in ET.iterparse(str(xml_path), events=('end',)):
            if elem.tag == 'sms':
                total_parsed += 1
                address = elem.get('address') or ""
                contact_name = elem.get('contact_name') or ""
                try:
                    date_epoch = int(elem.get('date', 0))
                except ValueError:
                    date_epoch = 0

                timestamp_ny = _epoch_to_ny_timestamp(date_epoch, elem.get('readable_date', ''))
                body = elem.get('body') or ""
                read_status = int(elem.get('read', 1) or 1)
                is_sent = 1 if elem.get('type') == '2' else 0

                counterparty = resolve_counterparty(contact_name, address, body)
                if counterparty:
                    partner_counts[counterparty] = partner_counts.get(counterparty, 0) + 1

                is_historical = 1 if (time.time() * 1000 - date_epoch) > 86400 * 1000 else 0
                batch.append((
                    'SMS', address, contact_name, date_epoch, timestamp_ny,
                    body, read_status, is_sent, counterparty, source_filename, is_historical
                ))
                if len(batch) >= batch_size:
                    flush_batch()
                elem.clear()

            elif elem.tag == 'mms':
                total_parsed += 1
                address = elem.get('address') or ""
                contact_name = elem.get('contact_name') or ""
                try:
                    date_epoch = int(elem.get('date', 0))
                except ValueError:
                    date_epoch = 0

                timestamp_ny = _epoch_to_ny_timestamp(date_epoch, elem.get('readable_date', ''))
                read_status = 1 if elem.get('read') == '1' else 0
                is_sent = 1 if elem.get('msg_box') == '2' else 0

                # Resolve address from <addrs> if top-level address is missing/placeholder
                if not address or "insert-address-token" in address.lower() or address == "~null~":
                    for a in elem.findall('.//addr'):
                        t = a.get('type')
                        a_addr = a.get('address', '')
                        if is_sent and t == '151' and a_addr and "insert-address-token" not in a_addr:
                            address = a_addr
                            break
                        elif not is_sent and t == '137' and a_addr and "insert-address-token" not in a_addr:
                            address = a_addr
                            break

                # Extract parts (text and attachments)
                texts = []
                attachments = []
                for p in elem.findall('.//part'):
                    ct = p.get('ct', '')
                    if ct == 'application/smil':
                        continue
                    t = p.get('text')
                    if t and t != 'null':
                        texts.append(t)
                    elif ct:
                        fn = p.get('name') or p.get('fn') or ct
                        if fn and fn != 'null':
                            attachments.append(fn)

                if texts:
                    body = "\n".join(texts).strip()
                    if attachments:
                        body += f" [Media: {', '.join(attachments)}]"
                elif attachments:
                    body = f"[Media Attachment: {', '.join(attachments)}]"
                else:
                    body = "[MMS Media / No Text]"

                counterparty = resolve_counterparty(contact_name, address, body)
                if counterparty:
                    partner_counts[counterparty] = partner_counts.get(counterparty, 0) + 1

                is_historical = 1 if (time.time() * 1000 - date_epoch) > 86400 * 1000 else 0
                batch.append((
                    'MMS', address, contact_name, date_epoch, timestamp_ny,
                    body, read_status, is_sent, counterparty, source_filename, is_historical
                ))
                if len(batch) >= batch_size:
                    flush_batch()
                elem.clear()

        flush_batch()

    elapsed = time.time() - t0
    logger.info(
        f"Completed SMS/MMS XML parse in {elapsed:.2f}s: "
        f"{total_parsed} parsed, {new_inserted} newly inserted into phone_sms_ingress."
    )
    if partner_counts:
        logger.info(f"Partner thread summary: {partner_counts}")
    return total_parsed, new_inserted, partner_counts


def parse_calls_xml(xml_path: Path, db_path: Path = DB_PATH) -> Tuple[int, int, Dict[str, int]]:
    """
    Stream-parse Call Log XML backup file into SQLite table phone_calls_ingress.
    Returns: (total_parsed, new_inserted, partner_counts)
    """
    total_parsed = 0
    new_inserted = 0
    partner_counts: Dict[str, int] = {}
    batch = []
    batch_size = 500
    source_filename = xml_path.name

    logger.info(f"Parsing Calls XML: {xml_path}...")
    t0 = time.time()

    with get_db(row_factory=False) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()

        def flush_batch():
            nonlocal new_inserted
            if not batch:
                return
            inserted_before = conn.total_changes
            cursor.executemany("""
                INSERT OR IGNORE INTO phone_calls_ingress (
                    number, contact_name, date_epoch, timestamp_ny, duration,
                    call_type, readable_date, counterparty, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, batch)
            conn.commit()
            new_inserted += (conn.total_changes - inserted_before)
            batch.clear()

        for event, elem in ET.iterparse(str(xml_path), events=('end',)):
            if elem.tag == 'call':
                total_parsed += 1
                number = elem.get('number') or ""
                contact_name = elem.get('contact_name') or ""
                try:
                    date_epoch = int(elem.get('date', 0))
                except ValueError:
                    date_epoch = 0

                try:
                    duration = int(elem.get('duration', 0))
                except ValueError:
                    duration = 0

                try:
                    call_type = int(elem.get('type', 1))
                except ValueError:
                    call_type = 1

                readable_date = elem.get('readable_date') or ""
                timestamp_ny = _epoch_to_ny_timestamp(date_epoch, readable_date)
                counterparty = resolve_counterparty(contact_name, number)
                if counterparty:
                    partner_counts[counterparty] = partner_counts.get(counterparty, 0) + 1

                batch.append((
                    number, contact_name, date_epoch, timestamp_ny, duration,
                    call_type, readable_date, counterparty, source_filename
                ))
                if len(batch) >= batch_size:
                    flush_batch()
                elem.clear()

        flush_batch()

    elapsed = time.time() - t0
    logger.info(
        f"Completed Calls XML parse in {elapsed:.2f}s: "
        f"{total_parsed} parsed, {new_inserted} newly inserted into phone_calls_ingress."
    )
    if partner_counts:
        logger.info(f"Calls partner thread summary: {partner_counts}")
    return total_parsed, new_inserted, partner_counts


def run_pipeline(sync: bool = True, parse: bool = True, target_file: Optional[Path] = None, all_files: bool = False) -> Dict[str, Any]:
    """Execute the full ingress pipeline."""
    init_db()

    if sync:
        sync_ok = sync_drive_backups()
        if not sync_ok and not target_file:
            logger.warning("Sync failed; proceeding to parse any existing local files.")

    results: Dict[str, Any] = {
        "sms_parsed": 0,
        "sms_new": 0,
        "calls_parsed": 0,
        "calls_new": 0,
        "sms_partners": {},
        "calls_partners": {}
    }

    if not parse:
        return results

    if target_file:
        files = [target_file]
    elif all_files:
        sms_files = sorted(LOCAL_SYNC_DIR.glob("sms-*.xml"), key=lambda p: p.stat().st_mtime, reverse=True)
        call_files = sorted(LOCAL_SYNC_DIR.glob("calls-*.xml"), key=lambda p: p.stat().st_mtime, reverse=True)
        files = sms_files + call_files
    else:
        # Default: newest cumulative snapshot only (< 3 seconds instead of 9 minutes)
        sms_files = sorted(LOCAL_SYNC_DIR.glob("sms-*.xml"), key=lambda p: p.stat().st_mtime, reverse=True)
        call_files = sorted(LOCAL_SYNC_DIR.glob("calls-*.xml"), key=lambda p: p.stat().st_mtime, reverse=True)
        files = ([sms_files[0]] if sms_files else []) + ([call_files[0]] if call_files else [])

    if not files:
        logger.info(f"No XML backup files found in {LOCAL_SYNC_DIR}.")
        return results

    for f in files:
        if not f.exists():
            continue
        if "sms-" in f.name:
            t_parsed, t_new, p_counts = parse_sms_xml(f)
            results["sms_parsed"] += t_parsed
            results["sms_new"] += t_new
            for k, v in p_counts.items():
                results["sms_partners"][k] = results["sms_partners"].get(k, 0) + v
        elif "calls-" in f.name:
            c_parsed, c_new, cp_counts = parse_calls_xml(f)
            results["calls_parsed"] += c_parsed
            results["calls_new"] += c_new
            for k, v in cp_counts.items():
                results["calls_partners"][k] = results["calls_partners"].get(k, 0) + v

    # Automatically project new records into comms_unified and update SQLite FTS5 search index
    try:
        from scripts.comms_indexer import run_indexing
        logger.info("Triggering automatic comms indexing and FTS5 search synchronization...")
        idx_summary = run_indexing()
        results["indexing"] = idx_summary
        logger.info(f"Comms indexing complete: {idx_summary}")
    except Exception as e:
        logger.error(f"Failed to execute automatic comms_indexer: {e}", exc_info=True)

    # Automatically compile un-synced SMS/RCS into canonical ledgers and weekly chronicles
    try:
        from scripts.sync_comms_to_chronicle import compile_unlogged_sms
        logger.info("Triggering automatic compilation of un-synced SMS/RCS to chronicles...")
        compiled_count = compile_unlogged_sms(dry_run=False)
        results["compiled_to_chronicle"] = compiled_count
        logger.info(f"Chronicle compilation complete: {compiled_count} record(s) compiled.")
        sync_gdrive_script = Path("/home/james/stacklabs/scripts/sync_to_gdrive.sh")
        if compiled_count > 0 and sync_gdrive_script.exists():
            logger.info("Triggering Google Drive replication script sync_to_gdrive.sh...")
            subprocess.run(["/bin/bash", str(sync_gdrive_script)], check=False)
    except Exception as e:
        logger.error(f"Failed to execute automatic compile_unlogged_sms: {e}", exc_info=True)
        results["compiled_to_chronicle"] = 0

    logger.info(f"Pipeline run summary: {results}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Hourly SMS & Call Log Backup Ingress Parser")
    parser.add_argument("--sync-and-parse", action="store_true", help="Sync from Google Drive and parse newest backup")
    parser.add_argument("--sync-only", action="store_true", help="Sync from Google Drive without parsing")
    parser.add_argument("--parse-only", action="store_true", help="Parse existing local backup files without syncing")
    parser.add_argument("--all", action="store_true", help="Parse all historical XML backup files instead of newest only")
    parser.add_argument("--file", type=str, help="Parse a single specified XML backup file")
    args = parser.parse_args()

    if args.sync_only:
        init_db()
        sync_drive_backups()
        return

    if args.file:
        target = Path(args.file)
        if not target.exists():
            logger.error(f"Target file not found: {target}")
            sys.exit(1)
        run_pipeline(sync=False, parse=True, target_file=target)
        return

    if args.parse_only:
        run_pipeline(sync=False, parse=True, all_files=args.all)
        return

    # Default: sync and parse
    run_pipeline(sync=True, parse=True, all_files=args.all)


if __name__ == "__main__":
    main()
