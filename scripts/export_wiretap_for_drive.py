#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Wiretap Exporter for Drive & Argon Batch Armory
Extracts rolling 24-hour chat slices, velocity peaks, and unmapped lexical anomalies
from data/morning_wiretap.db into clean, token-efficient JSONL packages for Drive sync.
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/export_wiretap_for_drive.py
"""
import argparse
import hashlib
import json
import logging
import os
import pathlib
import sqlite3
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

PROJECT_ROOT = pathlib.Path("/home/james/stacklabs")
DB_PATH = PROJECT_ROOT / "data" / "morning_wiretap.db"
EXPORT_DIR = PROJECT_ROOT / "data" / "exports" / "wiretap_slices"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("export_wiretap_for_drive")


def get_wal_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def export_rolling_slices(lookback_hours: int = 24) -> Dict[str, Any]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_wal_conn()
    cur = conn.cursor()

    cutoff_epoch = time.time() - (lookback_hours * 3600)
    timestamp_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # 1. Export High-Spike Chat Messages (Filtered to remove spam)
    spike_query = """
        SELECT id, channel_key, stream_id, author, message, epoch_time, is_spike, token_count
        FROM chat_telemetry
        WHERE epoch_time >= ? AND length(message) >= 4 AND message NOT LIKE '!%'
        ORDER BY epoch_time DESC LIMIT 5000
    """
    rows = cur.execute(spike_query, (cutoff_epoch,)).fetchall()
    
    chat_payload = [dict(r) for r in rows]
    chat_file = EXPORT_DIR / f"chat_telemetry_spikes_{timestamp_tag}.json"
    chat_file.write_text(json.dumps(chat_payload, indent=2), encoding="utf-8")
    logger.info(f"Exported {len(chat_payload)} spike chat messages to {chat_file.name}")

    # 2. Export Recent Toe-Tag Receipts
    toetag_rows = cur.execute(
        "SELECT * FROM toe_tag_receipts ORDER BY id DESC LIMIT 50" if "id" in [c[1] for c in cur.execute("PRAGMA table_info(toe_tag_receipts)").fetchall()]
        else "SELECT * FROM toe_tag_receipts LIMIT 50"
    ).fetchall()
    toetag_payload = [dict(r) for r in toetag_rows]
    toetag_file = EXPORT_DIR / f"toe_tag_receipts_{timestamp_tag}.json"
    toetag_file.write_text(json.dumps(toetag_payload, indent=2), encoding="utf-8")
    logger.info(f"Exported {len(toetag_payload)} toe-tag receipts to {toetag_file.name}")

    # 3. Export CFB Carnage Autopsies
    carnage_rows = cur.execute("SELECT * FROM cfb_carnage_autopsy ORDER BY last_synced_at DESC LIMIT 30").fetchall()
    carnage_payload = [dict(r) for r in carnage_rows]
    carnage_file = EXPORT_DIR / f"cfb_carnage_{timestamp_tag}.json"
    carnage_file.write_text(json.dumps(carnage_payload, indent=2), encoding="utf-8")
    logger.info(f"Exported {len(carnage_payload)} CFB carnage records to {carnage_file.name}")

    # 4. Write Manifest for Argon Armory ingestion
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "lookback_hours": lookback_hours,
        "files": {
            "chat_spikes": str(chat_file),
            "toe_tags": str(toetag_file),
            "cfb_carnage": str(carnage_file)
        },
        "counts": {
            "chat_spikes": len(chat_payload),
            "toe_tags": len(toetag_payload),
            "cfb_carnage": len(carnage_payload)
        }
    }
    manifest_file = EXPORT_DIR / "latest_armory_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    conn.close()
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Export rolling wiretap slices for Argon Drive armory")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours")
    args = parser.parse_args()

    manifest = export_rolling_slices(args.hours)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
