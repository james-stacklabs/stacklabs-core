#!/usr/bin/env python3
"""
TMI High-Leverage Phone Alert Dispatcher (Rosetta Stone Bytecode Edition)
Path: /home/james/stacklabs/scripts/tmi_phone_buzzer.py
Author: James Carroll (Lead Systems Architect)

Tails atomic SQLite WAL telemetry (tmi_live_events in ground_truth.db)
and fires sub-second mobile push notifications prefixed with shape-redundant
Rosetta Stone 4-gram bytecode headers on high-entropy game moments.
"""

import os
import sys
import time
import json
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# Paths
BASE_DIR = Path("/home/james/stacklabs")
DATA_DIR = BASE_DIR / "data"
GT_DB = DATA_DIR / "ground_truth.db"
DEDUPE_DB = DATA_DIR / "tmi_alert_dedupe.db"
ENV_FILE = BASE_DIR / ".env"

def load_env():
    """Load environment variables dynamically from .env file."""
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def init_tables():
    """Ensure atomic ground_truth table and deduplication database exist in WAL mode."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Ensure tmi_live_events exists with bytecode columns
    with sqlite3.connect(GT_DB) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tmi_live_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                event_id TEXT UNIQUE NOT NULL,
                priority TEXT NOT NULL DEFAULT 'P1',
                event_type TEXT NOT NULL,
                headline TEXT NOT NULL,
                details TEXT,
                leverage_index REAL DEFAULT 0.0,
                inning TEXT,
                score TEXT,
                emoji_frame TEXT DEFAULT '',
                ascii_frame TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tmi_events_id ON tmi_live_events(id);")
        
        # Verify schema columns
        cursor = conn.execute("PRAGMA table_info(tmi_live_events);")
        cols = [r[1] for r in cursor.fetchall()]
        if "emoji_frame" not in cols:
            conn.execute("ALTER TABLE tmi_live_events ADD COLUMN emoji_frame TEXT DEFAULT '';")
        if "ascii_frame" not in cols:
            conn.execute("ALTER TABLE tmi_live_events ADD COLUMN ascii_frame TEXT DEFAULT '';")
        conn.commit()

    # 2. Ensure dedupe ledger exists
    with sqlite3.connect(DEDUPE_DB) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dispatched_alerts (
                event_id TEXT PRIMARY KEY,
                game_id TEXT,
                event_type TEXT,
                headline TEXT,
                emoji_frame TEXT DEFAULT '',
                dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor = conn.execute("PRAGMA table_info(dispatched_alerts);")
        dedupe_cols = [r[1] for r in cursor.fetchall()]
        if "emoji_frame" not in dedupe_cols:
            conn.execute("ALTER TABLE dispatched_alerts ADD COLUMN emoji_frame TEXT DEFAULT '';")
        conn.commit()

def is_already_dispatched(event_id: str) -> bool:
    """Check if event has already been sent to prevent multi-buzzing."""
    with sqlite3.connect(DEDUPE_DB) as conn:
        cursor = conn.execute("SELECT 1 FROM dispatched_alerts WHERE event_id = ?", (event_id,))
        return cursor.fetchone() is not None

def record_dispatch(event_id: str, game_id: str, event_type: str, headline: str, emoji_frame: str = ""):
    """Record event ID in SQLite dedupe ledger."""
    with sqlite3.connect(DEDUPE_DB) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO dispatched_alerts (event_id, game_id, event_type, headline, emoji_frame) VALUES (?, ?, ?, ?, ?)",
            (event_id, game_id, event_type, headline, emoji_frame)
        )
        conn.commit()

def send_push(title: str, message: str, priority: int = 2):
    """
    Dispatch push alert using configured provider from .env.
    Supports NTFY_TOPIC, ALERT_PHONE_WEBHOOK, or Pushover.
    """
    ntfy_topic = os.getenv("NTFY_TOPIC", "stacklabs_precog")
    webhook_url = os.getenv("ALERT_PHONE_WEBHOOK")
    pushover_user = os.getenv("PUSHOVER_USER_KEY")
    pushover_token = os.getenv("PUSHOVER_APP_TOKEN")
    sent = False

    # 1. ntfy.sh (Fastest zero-auth push protocol, default sub-200ms latency)
    if ntfy_topic:
        url = f"https://ntfy.sh/{ntfy_topic}"
        headers = {
            "Title": title.encode("utf-8"),
            "Priority": str(priority),
            "Tags": "baseball,zap,loudspeaker"
        }
        req = urllib.request.Request(url, data=message.encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    sent = True
        except Exception as e:
            sys.stderr.write(f"ntfy dispatch error: {e}\n")

    # 2. Generic HTTP Webhook (Discord / Slack / Custom Gateway)
    if webhook_url and not sent:
        payload = json.dumps({"title": title, "body": message, "text": f"*{title}*\n{message}"}).encode("utf-8")
        req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status in (200, 204):
                    sent = True
        except Exception as e:
            sys.stderr.write(f"webhook dispatch error: {e}\n")

    # 3. Pushover API
    if pushover_user and pushover_token and not sent:
        url = "https://api.pushover.net/1/messages.json"
        data = urllib.parse.urlencode({
            "token": pushover_token,
            "user": pushover_user,
            "title": title,
            "message": message,
            "priority": priority
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    sent = True
        except Exception as e:
            sys.stderr.write(f"pushover dispatch error: {e}\n")

    if not sent:
        sys.stderr.write(f"[FALLBACK LOG ONLY] {title} -> {message}\n")

def poll_tmi_events(last_id: int) -> int:
    """Inspect atomic SQLite WAL table and trigger alerts on high-entropy plays."""
    with sqlite3.connect(GT_DB, timeout=2.0) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT id, game_id, event_id, priority, event_type, headline, details, inning, score, emoji_frame, ascii_frame
            FROM tmi_live_events
            WHERE id > ? AND priority IN ('P0', 'P1')
            ORDER BY id ASC
        """, (last_id,))
        rows = cursor.fetchall()

    for r in rows:
        row_id = r["id"]
        event_id = r["event_id"]
        game_id = r["game_id"]
        priority_code = r["priority"]
        ev_type = r["event_type"]
        headline = r["headline"]
        details = r["details"] or ""
        inning = r["inning"] or "Live"
        score = r["score"] or ""
        emoji_frame = r["emoji_frame"] or "⚾🛑📈🚀"
        ascii_frame = r["ascii_frame"] or "[MLB][CRT][SPK][DSP]"

        last_id = max(last_id, row_id)

        if is_already_dispatched(event_id):
            continue

        # Prefix title with emoji frame for instant lock-screen shape triage
        title = f"{emoji_frame} [{ev_type}] {inning} ({score})".strip()
        msg = f"{headline}\n{details}".strip()
        push_priority = 2 if priority_code == "P0" else 1

        send_push(title, msg, priority=push_priority)
        record_dispatch(event_id, game_id, ev_type, headline, emoji_frame)
        sys.stdout.write(f"{ascii_frame} Dispatched TMI {priority_code} Event: {event_id} -> {title}\n")
        sys.stdout.flush()

    return last_id

def get_max_existing_id() -> int:
    """Return max rowid to avoid historical event replay on fresh boot."""
    try:
        with sqlite3.connect(GT_DB, timeout=2.0) as conn:
            cursor = conn.execute("SELECT COALESCE(MAX(id), 0) FROM tmi_live_events")
            row = cursor.fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return 0

def main():
    load_env()
    init_tables()
    last_id = get_max_existing_id()

    sys.stdout.write(f"TMI Phone Buzzer active on Clio metal (Rosetta Stone Bytecode). High-water mark ID: {last_id}\n")
    sys.stdout.flush()

    while True:
        try:
            last_id = poll_tmi_events(last_id)
        except Exception as e:
            sys.stderr.write(f"Error in TMI telemetry poll loop: {e}\n")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
