#!/usr/bin/env python3
"""
Sovereign OS — Pixel 10a SMS & RCS Ingress Gateway (Tool #43 Extension)
Path: /home/james/stacklabs/scripts/sms_ingress.py
Endpoint: POST /api/ingress/sms (Mounted on Port 8088)

Receives structured SMS/RCS webhook events from MacroDroid on Pilot's Pixel 10a over Tailscale.
Atomically routes and splices correspondence into the canonical counterparties ledger
(Pawel Rudnicki, Jeremy Malone, Jeff U'Ren, or Weekly General Chronicle) using fcntl.flock.
"""

import os
import re
import sys
import time
import fcntl
import sqlite3
import logging
from datetime import datetime, timezone
import zoneinfo
from pathlib import Path
from flask import Blueprint, request, jsonify

logger = logging.getLogger("SMS_Ingress")

sms_ingress_bp = Blueprint("sms_ingress", __name__)

BASE_DIR = Path(os.environ.get("SOVEREIGN_ROOT", "/home/james"))
LEDGER_PAWEL_JEREMY = BASE_DIR / "SovereignOS" / "dna" / "docs" / "13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md"
LEDGER_JEFF_UREN = BASE_DIR / "sovereign_inbox" / "notebook_sync" / "11_JeffUren_Prospectus" / "01_CANONICAL_COMMUNICATIONS_LOG_AND_OPERATOR_DOSSIER_JEFF_UREN.md"
LEDGER_WEEKLY = BASE_DIR / "sovereign_inbox" / "notebook_sync" / "StackLabs_Internal" / "epoch_sources" / "SESSION_CHRONICLE_CURRENT_WEEK.md"
AUDIT_DB_PATH = BASE_DIR / "sovereign_inbox" / "pilot_drops" / "screenshots" / "chronicle_audit.db"
SCRATCH_PAD_PATH = BASE_DIR / "sovereign_inbox" / "pilot_drops" / "scratch_pad.md"


def resolve_counterparty(contact_name: str, sender: str, body: str) -> dict:
    """Resolve counterparty target ledger and sequence prefix."""
    search_space = f"{contact_name} {sender} {body}".lower()
    
    if "pawel" in search_space or "rudnicki" in search_space:
        return {
            "type": "pawel",
            "name": "Pawel Rudnicki",
            "ledger_path": LEDGER_PAWEL_JEREMY,
            "tag_prefix": "LOG-PR",
            "section_header": "## 🏛️ SECTION I: PAWEL RUDNICKI",
            "next_section_header": "## 🚜 SECTION II: JEREMY MALONE"
        }
    elif "jeremy" in search_space or "malone" in search_space or "davidson" in search_space:
        return {
            "type": "jeremy",
            "name": "Jeremy Malone",
            "ledger_path": LEDGER_PAWEL_JEREMY,
            "tag_prefix": "LOG-JM",
            "section_header": "## 🚜 SECTION II: JEREMY MALONE",
            "next_section_header": "## 🦞 3. JIM CARROLL"
        }
    elif "jeff" in search_space or "uren" in search_space or "u'ren" in search_space:
        return {
            "type": "jeff",
            "name": "Jeff U'Ren",
            "ledger_path": LEDGER_JEFF_UREN,
            "tag_prefix": "LOG-JU",
            "section_header": "### 2. CANONICAL COMMUNICATIONS & PROBE LOG",
            "next_section_header": "### 3. VOICE & DIALOGUE GOVERNANCE GUIDELINES"
        }
    else:
        return {
            "type": "general",
            "name": contact_name if contact_name else sender,
            "ledger_path": LEDGER_WEEKLY,
            "tag_prefix": "LOG-GEN",
            "section_header": None,
            "next_section_header": None
        }


def get_next_sequence_tag(content: str, tag_prefix: str) -> str:
    """Find highest existing sequence tag and increment."""
    pattern = rf"\[{re.escape(tag_prefix)}-(\d+)\]"
    matches = re.findall(pattern, content)
    if matches:
        highest = max(int(m) for m in matches)
        return f"[{tag_prefix}-{highest + 1:03d}]"
    return f"[{tag_prefix}-001]"


def record_audit(tag: str, counterparty: str, sender: str, body: str, ledger: str):
    """Log to SQLite chronicle_audit.db in WAL mode."""
    try:
        AUDIT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(AUDIT_DB_PATH, timeout=5.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chronicle_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_filename TEXT NOT NULL,
                    archived_path TEXT,
                    file_sha256 TEXT NOT NULL,
                    counterparty_name TEXT,
                    sequence_tag TEXT,
                    target_ledger TEXT,
                    message_timestamp TEXT,
                    raw_json TEXT,
                    status TEXT NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT INTO chronicle_audit 
                (original_filename, archived_path, file_sha256, counterparty_name, sequence_tag, target_ledger, message_timestamp, raw_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"MACRODROID_SMS_{int(time.time())}",
                "macro_droid_webhook",
                "direct_sms_stream",
                counterparty,
                tag,
                str(ledger),
                datetime.now().isoformat(),
                body[:500],
                "CHISELED"
            ))
            conn.commit()
    except Exception as e:
        logger.warning(f"Audit log failed: {e}")


def notify_scratchpad(tag: str, counterparty: str, body: str):
    """Append brief alert to scratch_pad.md."""
    if SCRATCH_PAD_PATH.exists():
        try:
            preview = body.strip().replace("\n", " ")[:80]
            alert = f"\n- **⚡ [MOBILE SMS INGRESS]** {tag} from **{counterparty}**: \"{preview}...\" ({datetime.now().strftime('%H:%M:%S EDT')})\n"
            with open(SCRATCH_PAD_PATH, "a", encoding="utf-8") as f:
                f.write(alert)
        except Exception as e:
            logger.warning(f"Scratchpad alert failed: {e}")


@sms_ingress_bp.route("/api/ingress/sms", methods=["POST"])
def handle_sms_ingress():
    """
    Ingest SMS/RCS message from MacroDroid.
    Expected JSON:
    {
        "sender": "+1615...",
        "contact_name": "Jeremy Malone",
        "body": "Hey James...",
        "timestamp": "2026-09-28 15:10:00"
    }
    """
    data = request.get_json(silent=True) or {}
    
    # Resilient field extraction supporting both Port 8088 & Port 8095 payloads
    sender = str(data.get("sender") or data.get("phone_number") or data.get("contact_name") or data.get("not_title") or "Unknown").strip()
    contact_name = str(data.get("contact_name") or data.get("name") or data.get("not_title") or sender).strip()
    body = str(data.get("body") or data.get("message") or data.get("not_body") or "").strip()
    raw_timestamp = str(data.get("timestamp") or "").strip()
    direction = str(data.get("direction") or "INBOUND").strip().upper()

    if not body:
        return jsonify({"status": "error", "error": "Empty message body"}), 400

    # Determine timestamp in Eastern Time
    eastern = zoneinfo.ZoneInfo("America/New_York")
    now_eastern = datetime.now(eastern)
    time_str = raw_timestamp if raw_timestamp else now_eastern.strftime("%Y-%m-%d %H:%M:%S EDT")

    route = resolve_counterparty(contact_name, sender, body)
    ledger_path = route["ledger_path"]
    tag_prefix = route["tag_prefix"]
    counterparty = route["name"]

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if not ledger_path.exists():
        ledger_path.write_text("# CANONICAL COMMUNICATIONS LOG\n\n", encoding="utf-8")

    # Format Markdown Entry
    with open(ledger_path, "r+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            content = f.read()
            seq_tag = get_next_sequence_tag(content, tag_prefix)
            
            clean_body = body.replace("\n", "\n  > ")
            entry_md = (
                f"### {seq_tag} {time_str} — {direction.title()} Mobile SMS\n"
                f"* **Direction:** {direction} (Mobile SMS/RCS via Pixel 10a MacroDroid Bridge)\n"
                f"* **Actors:** {counterparty}, James Carroll (Pilot)\n"
                f"* **Evidence:** `MacroDroid SMS Event from {sender}`\n"
                f"* **Verbatim Transcript:**\n"
                f"  > **{counterparty}:** *\"{clean_body}\"*\n"
                f"* **Strategic Significance & Governance Analysis:**\n"
                f"  1. Direct mobile correspondence ingested via private Tailscale webhook.\n"
                f"  2. Zero manual transcription friction; atomic ledger integrity preserved.\n"
                f"* **Status:** PROCESSED & CHISELED\n"
            )

            next_marker = route["next_section_header"]
            if next_marker and next_marker in content:
                idx = content.find(next_marker)
                prefix = content[:idx].rstrip()
                if prefix.endswith("---"):
                    prefix = prefix[:-3].rstrip()
                new_content = prefix + "\n\n" + entry_md + "\n---\n\n" + content[idx:]
            else:
                new_content = content.rstrip() + "\n\n" + entry_md + "\n"

            f.seek(0)
            f.write(new_content)
            f.truncate()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    record_audit(seq_tag, counterparty, sender, body, str(ledger_path))
    notify_scratchpad(seq_tag, counterparty, body)

    return jsonify({
        "status": "success",
        "tag": seq_tag,
        "counterparty": counterparty,
        "ledger": str(ledger_path)
    }), 200


@sms_ingress_bp.route("/api/ingress/sms/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "Pixel 10a SMS Ingress Gateway (Port 8088)"}), 200
