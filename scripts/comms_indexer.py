#!/usr/bin/env python3
"""
scripts/comms_indexer.py — Unified Comms Search Indexer & SQLite FTS5 Engine
=============================================================================
System: Clio Dedicated Workstation
Work Order: WO0011104-BUILD-CENTRAL-COMMS-SEARCH-COCKPIT-AND-FTS5-ENGINE

Aggregates communications across:
  - Android SMS / MMS / RCS XML logs (via phone_sms_ingress)
  - Phone call logs (via phone_calls_ingress)
  - Screenshot OCR texts (pilot_drops/*_ocr.txt)
  - Notes & emails in vault/by_person/

Indexes all records into SQLite FTS5 table `comms_unified_fts` in `dna/sovereign_now.db`.
"""

import os
import re
import sys
import time
import zoneinfo
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.db import get_db
from scripts.sms_backup_parser import resolve_counterparty, _epoch_to_ny_timestamp

# Paths
DB_PATH = Path("/home/james/stacklabs/dna/sovereign_now.db")
PILOT_DROPS_DIR = Path("/home/james/stacklabs/pilot_drops")
VAULT_PERSON_DIR = Path("/home/james/stacklabs/vault/by_person")
LOG_FILE = Path("/home/james/stacklabs/logs/comms_indexer.log")

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CommsIndexer")

# Canonical person slug mapping
PERSON_SLUG_MAP = {
    "pawel_rudnicki": "Pawel Rudnicki",
    "pawel": "Pawel Rudnicki",
    "jeremy_malone": "Jeremy Malone",
    "jeremy": "Jeremy Malone",
    "jeff_schroeder": "Jeff Schroeder",
    "jeff schroeder": "Jeff Schroeder",
    "schroeder": "Jeff Schroeder",
    "vaporware": "Jeff Schroeder",
    "jeff_uren": "Jeff U'Ren",
    "jeff": "Jeff U'Ren",
    "cherlyn": "Cherylyn",
    "cherylyn": "Cherylyn",
    "barb": "Barb",
    "barb_baker": "Barb",
    "nick": "Nick",
    "lisa_calhoun": "Lisa Calhoun",
    "stephen_emery": "Stephen Emery",
    "eileen_carroll": "Eileen Carroll",
    "eileen": "Eileen Carroll",
}


def init_comms_schema(conn) -> None:
    """Create comms_unified table, indexes, and FTS5 virtual table with auto-sync triggers."""
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS comms_unified (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,       -- 'SMS', 'MMS', 'RCS', 'CALL', 'OCR', 'EMAIL', 'NOTE'
            counterparty TEXT,               -- 'Pawel Rudnicki', 'Cherylyn', 'Jeremy Malone', 'Barb', etc.
            address TEXT DEFAULT '',          -- Phone number or email address
            timestamp_ny TEXT NOT NULL,      -- 'YYYY-MM-DD HH:MM:SS EDT'
            date_epoch INTEGER NOT NULL,     -- Unix epoch (ms)
            is_sent INTEGER DEFAULT 0,       -- 1 = Outbound from James, 0 = Inbound
            subject TEXT DEFAULT '',         -- Subject line or filename
            body TEXT NOT NULL,              -- Full message or OCR body
            source_file TEXT DEFAULT '',     -- Originating file or path
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_comms_unified_dedupe 
        ON comms_unified (date_epoch, address, body);
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_comms_unified_counterparty 
        ON comms_unified (counterparty);
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_comms_unified_source_type 
        ON comms_unified (source_type);
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_comms_unified_epoch 
        ON comms_unified (date_epoch DESC);
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS comms_unified_fts USING fts5(
            body,
            counterparty,
            subject,
            address,
            content='comms_unified',
            content_rowid='id'
        );
    """)

    # FTS5 External Content Triggers for real-time synchronization
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_comms_unified_ai AFTER INSERT ON comms_unified BEGIN
            INSERT INTO comms_unified_fts(rowid, body, counterparty, subject, address)
            VALUES (new.id, new.body, new.counterparty, new.subject, new.address);
        END;
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_comms_unified_ad AFTER DELETE ON comms_unified BEGIN
            INSERT INTO comms_unified_fts(comms_unified_fts, rowid, body, counterparty, subject, address)
            VALUES('delete', old.id, old.body, old.counterparty, old.subject, old.address);
        END;
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_comms_unified_au AFTER UPDATE ON comms_unified BEGIN
            INSERT INTO comms_unified_fts(comms_unified_fts, rowid, body, counterparty, subject, address)
            VALUES('delete', old.id, old.body, old.counterparty, old.subject, old.address);
            INSERT INTO comms_unified_fts(rowid, body, counterparty, subject, address)
            VALUES (new.id, new.body, new.counterparty, new.subject, new.address);
        END;
    """)
    conn.commit()


def index_sms_ingress(conn) -> int:
    """Ingest rows from phone_sms_ingress into comms_unified."""
    cur = conn.cursor()
    cur.execute("""
        SELECT message_type, address, contact_name, date_epoch, timestamp_ny, body, is_sent, counterparty, source_file
        FROM phone_sms_ingress
        WHERE body IS NOT NULL AND trim(body) != ''
    """)
    rows = cur.fetchall()
    batch = []
    for r in rows:
        m_type = r[0] or "SMS"
        addr = r[1] or ""
        contact = r[2] or ""
        d_epoch = int(r[3])
        ts_ny = r[4] or _epoch_to_ny_timestamp(d_epoch)
        body = r[5] or ""
        is_sent = int(r[6] or 0)
        counterparty = r[7] or resolve_counterparty(contact, addr, body)
        source_file = r[8] or ""

        batch.append((
            m_type, counterparty, addr, ts_ny, d_epoch, is_sent, "", body, source_file
        ))

    before = conn.total_changes
    cur.executemany("""
        INSERT OR IGNORE INTO comms_unified (
            source_type, counterparty, address, timestamp_ny, date_epoch, is_sent, subject, body, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, batch)
    conn.commit()
    inserted = conn.total_changes - before
    logger.info(f"Indexed SMS/MMS/RCS: {len(batch)} processed, {inserted} newly inserted into comms_unified.")
    return inserted


def index_calls_ingress(conn) -> int:
    """Ingest rows from phone_calls_ingress into comms_unified."""
    cur = conn.cursor()
    cur.execute("""
        SELECT number, contact_name, date_epoch, timestamp_ny, duration, call_type, readable_date, counterparty, source_file
        FROM phone_calls_ingress
    """)
    rows = cur.fetchall()
    batch = []
    for r in rows:
        number = r[0] or ""
        contact = r[1] or ""
        d_epoch = int(r[2])
        ts_ny = r[3] or _epoch_to_ny_timestamp(d_epoch, r[6] or "")
        duration = int(r[4] or 0)
        call_type = int(r[5] or 1)
        counterparty = r[7] or resolve_counterparty(contact, number)
        source_file = r[8] or ""

        is_sent = 1 if call_type == 2 else 0
        call_label = "Outgoing Call" if call_type == 2 else ("Incoming Call" if call_type == 1 else "Missed Call")
        contact_display = contact or number or "Unknown"
        subject = f"{call_label} ({duration}s)"
        body = f"{call_label} with {contact_display}. Duration: {duration} seconds."

        batch.append((
            "CALL", counterparty, number, ts_ny, d_epoch, is_sent, subject, body, source_file
        ))

    before = conn.total_changes
    cur.executemany("""
        INSERT OR IGNORE INTO comms_unified (
            source_type, counterparty, address, timestamp_ny, date_epoch, is_sent, subject, body, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, batch)
    conn.commit()
    inserted = conn.total_changes - before
    logger.info(f"Indexed Phone Calls: {len(batch)} processed, {inserted} newly inserted into comms_unified.")
    return inserted


def index_ocr_files(conn) -> int:
    """Ingest screenshot OCR text files from pilot_drops/*_ocr.txt into comms_unified."""
    if not PILOT_DROPS_DIR.exists():
        return 0

    ocr_files = sorted(PILOT_DROPS_DIR.glob("*_ocr.txt"))
    batch = []
    eastern = zoneinfo.ZoneInfo("America/New_York")

    for f in ocr_files:
        try:
            body = f.read_text(encoding="utf-8", errors="replace").strip()
            if not body or body.startswith("[OCR Error:"):
                continue

            st = f.stat()
            mtime_epoch = int(st.st_mtime * 1000)
            ts_ny = datetime.fromtimestamp(st.st_mtime, tz=eastern).strftime("%Y-%m-%d %H:%M:%S %Z")
            subject = f"Screenshot OCR: {f.name}"
            counterparty = resolve_counterparty("", "", body)

            batch.append((
                "OCR", counterparty, "", ts_ny, mtime_epoch, 0, subject, body, f.name
            ))
        except Exception as e:
            logger.warning(f"Error reading OCR file {f}: {e}")

    before = conn.total_changes
    cur = conn.cursor()
    cur.executemany("""
        INSERT OR IGNORE INTO comms_unified (
            source_type, counterparty, address, timestamp_ny, date_epoch, is_sent, subject, body, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, batch)
    conn.commit()
    inserted = conn.total_changes - before
    logger.info(f"Indexed OCR drops: {len(batch)} processed, {inserted} newly inserted into comms_unified.")
    return inserted


def _parse_vault_markdown(file_path: Path) -> Optional[Dict[str, Any]]:
    """Parse YAML frontmatter and body from a vault markdown document."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    frontmatter: Dict[str, str] = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2].strip()
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    frontmatter[k.strip().lower()] = v.strip()

    # Determine counterparty
    person_key = frontmatter.get("person", "")
    counterparty = PERSON_SLUG_MAP.get(person_key)
    if not counterparty:
        parent_slug = file_path.parent.parent.name
        counterparty = PERSON_SLUG_MAP.get(parent_slug)
    if not counterparty:
        counterparty = resolve_counterparty(person_key, "", body)

    # Determine source_type
    doc_type = frontmatter.get("type", "").upper()
    if not doc_type:
        parent_dir = file_path.parent.name.lower()
        if parent_dir == "email":
            doc_type = "EMAIL"
        elif parent_dir == "notes":
            doc_type = "NOTE"
        elif parent_dir == "sms":
            doc_type = "SMS"
        else:
            doc_type = "NOTE"

    # Subject / Title
    subject = frontmatter.get("title", "")
    if not subject:
        for line in body.splitlines():
            if line.startswith("# "):
                subject = line.lstrip("# ").strip()
                break
    if not subject:
        subject = file_path.stem

    # Timestamp & Epoch
    date_str = frontmatter.get("date", "")
    eastern = zoneinfo.ZoneInfo("America/New_York")
    d_epoch = int(file_path.stat().st_mtime * 1000)
    ts_ny = datetime.fromtimestamp(file_path.stat().st_mtime, tz=eastern).strftime("%Y-%m-%d %H:%M:%S %Z")

    # Check filename for YYYYMMDD_HHMM
    m = re.match(r'^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})', file_path.stem)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                          int(m.group(4)), int(m.group(5)), tzinfo=eastern)
            d_epoch = int(dt.timestamp() * 1000)
            ts_ny = dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            pass
    elif date_str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=eastern)
            d_epoch = int(dt.timestamp() * 1000)
            ts_ny = dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            pass

    sender = frontmatter.get("sender", "").lower()
    is_sent = 1 if ("outbound" in sender or "james carroll" in sender) else 0

    return {
        "source_type": doc_type,
        "counterparty": counterparty,
        "address": frontmatter.get("address", ""),
        "timestamp_ny": ts_ny,
        "date_epoch": d_epoch,
        "is_sent": is_sent,
        "subject": subject,
        "body": body,
        "source_file": str(file_path.relative_to(PROJECT_ROOT)) if file_path.is_relative_to(PROJECT_ROOT) else str(file_path)
    }


def index_vault_files(conn) -> int:
    """Ingest emails, notes, and milestones from vault/by_person/ into comms_unified."""
    if not VAULT_PERSON_DIR.exists():
        return 0

    md_files = sorted(VAULT_PERSON_DIR.glob("*/*/*.md"))
    batch = []
    for f in md_files:
        parsed = _parse_vault_markdown(f)
        if parsed and parsed["body"]:
            batch.append((
                parsed["source_type"],
                parsed["counterparty"],
                parsed["address"],
                parsed["timestamp_ny"],
                parsed["date_epoch"],
                parsed["is_sent"],
                parsed["subject"],
                parsed["body"],
                parsed["source_file"]
            ))

    before = conn.total_changes
    cur = conn.cursor()
    cur.executemany("""
        INSERT OR IGNORE INTO comms_unified (
            source_type, counterparty, address, timestamp_ny, date_epoch, is_sent, subject, body, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, batch)
    conn.commit()
    inserted = conn.total_changes - before
    logger.info(f"Indexed Vault files: {len(batch)} processed, {inserted} newly inserted into comms_unified.")
    return inserted


def rebuild_fts_index(conn) -> int:
    """Rebuild the SQLite FTS5 table from scratch using internal content table."""
    logger.info("Rebuilding comms_unified_fts index...")
    t0 = time.time()
    conn.execute("INSERT INTO comms_unified_fts(comms_unified_fts) VALUES('rebuild');")
    conn.commit()
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM comms_unified_fts;")
    fts_count = cur.fetchone()[0]
    elapsed = time.time() - t0
    logger.info(f"Rebuilt comms_unified_fts in {elapsed:.3f}s: {fts_count} total indexed documents.")
    return fts_count


def _sync_recent_counterparty_tokens_to_shm(conn) -> int:
    """Scan newly indexed inbound counterparty messages and emit salient tokens to /dev/shm."""
    try:
        from scripts.core.shm_counterparty_bus import emit_counterparty_tokens_to_shm
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT counterparty, body, date_epoch
            FROM comms_unified
            WHERE is_sent = 0 AND counterparty IS NOT NULL AND counterparty != ''
            ORDER BY id DESC LIMIT 50
        """).fetchall()
        emitted = 0
        for cp, body, date_epoch in rows:
            ts_sec = int(date_epoch / 1000) if (date_epoch and date_epoch > 1e11) else int(date_epoch or time.time())
            if emit_counterparty_tokens_to_shm(sender=str(cp), raw_snippet=str(body), timestamp_epoch=ts_sec):
                emitted += 1
        logger.info(f"Emitted {emitted} counterparty token envelopes to /dev/shm/vfs/comms/.")
        return emitted
    except Exception as exc:
        logger.warning(f"Failed emitting counterparty tokens to shm: {exc}")
        return 0


def run_indexing(rebuild: bool = False) -> Dict[str, Any]:
    """Execute the full indexing pipeline."""
    t0 = time.time()
    with get_db(row_factory=False) as conn:
        init_comms_schema(conn)

        sms_new = index_sms_ingress(conn)
        calls_new = index_calls_ingress(conn)
        ocr_new = index_ocr_files(conn)
        vault_new = index_vault_files(conn)

        # Check if FTS needs initial population or rebuild
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM comms_unified;")
        total_unified = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM comms_unified_fts;")
        total_fts = cur.fetchone()[0]

        if rebuild or total_fts < total_unified:
            total_fts = rebuild_fts_index(conn)

        # WO0011232: Post-index hook emits tokens to zero-lock /dev/shm bus
        shm_emitted = _sync_recent_counterparty_tokens_to_shm(conn)

    duration = time.time() - t0
    summary = {
        "status": "success",
        "duration_seconds": round(duration, 3),
        "sms_new": sms_new,
        "calls_new": calls_new,
        "ocr_new": ocr_new,
        "vault_new": vault_new,
        "shm_emitted": shm_emitted,
        "total_records": total_unified,
        "fts_indexed_records": total_fts
    }
    logger.info(f"Indexing completed: {summary}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Unified Comms Indexer & FTS5 Engine")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild of FTS5 search index")
    args = parser.parse_args()

    run_indexing(rebuild=args.rebuild)


if __name__ == "__main__":
    main()
