#!/usr/bin/env python3
"""
StackLabs TMI Live Event Emitter CLI
Path: /home/james/stacklabs/scripts/emit_tmi_event.py
Author: James Carroll (Lead Systems Architect)

Encodes telemetry events using the Rosetta Stone SLM Emoji Bytecode protocol
and commits atomic rows to tmi_live_events in data/ground_truth.db (SQLite WAL).
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

BASE_DIR = Path("/home/james/stacklabs")
DATA_DIR = BASE_DIR / "data"
GT_DB = DATA_DIR / "ground_truth.db"

# Ensure core library is on path
sys.path.insert(0, str(BASE_DIR))
from scripts.core.emoji_bytecode import EmojiCodebook, EmojiFrame, GuardrailViolationError

def init_db(conn: sqlite3.Connection):
    """Ensure table exists with emoji_frame and ascii_frame columns."""
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
    
    # Check if migration needed on existing table
    cursor = conn.execute("PRAGMA table_info(tmi_live_events);")
    columns = [row[1] for row in cursor.fetchall()]
    if "emoji_frame" not in columns:
        conn.execute("ALTER TABLE tmi_live_events ADD COLUMN emoji_frame TEXT DEFAULT '';")
    if "ascii_frame" not in columns:
        conn.execute("ALTER TABLE tmi_live_events ADD COLUMN ascii_frame TEXT DEFAULT '';")
    conn.commit()

def emit_event(
    game_id: str,
    event_id: str,
    event_type: str,
    headline: str,
    priority: str = "P1",
    details: str = "",
    leverage_index: float = 0.0,
    inning: str = "Live",
    score: str = "",
    subsystem: str = "sports_statcast",
    state: str = "critical",
    metric: str = "spike",
    action: str = "dispatch",
    target: str = ""
) -> EmojiFrame:
    """Encode 4-gram frame and insert into SQLite WAL."""
    codebook = EmojiCodebook()
    
    # Target tail defaults to event_type if unspecified
    effective_target = target or event_type

    # Compile the 4-gram frame
    frame = codebook.encode_from_slugs(
        subsystem=subsystem,
        state=state,
        metric=metric,
        action=action,
        target=effective_target
    )

    emoji_str = frame.to_frame_string()
    ascii_str = frame.to_log_string(codebook)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(GT_DB, timeout=2.0) as conn:
        init_db(conn)
        conn.execute("""
            INSERT OR REPLACE INTO tmi_live_events 
            (game_id, event_id, priority, event_type, headline, details, leverage_index, inning, score, emoji_frame, ascii_frame)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_id, event_id, priority, event_type, headline, details,
            leverage_index, inning, score, emoji_str, ascii_str
        ))
        conn.commit()

    sys.stdout.write(f"[EMIT TMI] {ascii_str} -> {headline} ({emoji_str})\n")
    sys.stdout.flush()
    return frame

def main():
    parser = argparse.ArgumentParser(description="Emit high-leverage TMI event with Rosetta Stone Bytecode")
    parser.add_argument("--game-id", required=True, help="Canonical game ID (e.g. G823576)")
    parser.add_argument("--event-id", default="", help="Unique event ID (defaults to timestamp-based)")
    parser.add_argument("--event-type", required=True, help="Classification slug (e.g. HR, WALKOFF, REDZONE)")
    parser.add_argument("--headline", required=True, help="Short human headline")
    parser.add_argument("--priority", default="P1", choices=["P0", "P1", "P2"])
    parser.add_argument("--details", default="", help="Statcast telemetry description")
    parser.add_argument("--leverage-index", type=float, default=2.5)
    parser.add_argument("--inning", default="Live")
    parser.add_argument("--score", default="")
    parser.add_argument("--subsystem", default="sports_statcast")
    parser.add_argument("--state", default="critical")
    parser.add_argument("--metric", default="spike")
    parser.add_argument("--action", default="dispatch")
    parser.add_argument("--target", default="")

    args = parser.parse_args()
    ev_id = args.event_id or f"ev_{int(time.time() * 1000)}"

    try:
        emit_event(
            game_id=args.game_id,
            event_id=ev_id,
            event_type=args.event_type,
            headline=args.headline,
            priority=args.priority,
            details=args.details,
            leverage_index=args.leverage_index,
            inning=args.inning,
            score=args.score,
            subsystem=args.subsystem,
            state=args.state,
            metric=args.metric,
            action=args.action,
            target=args.target
        )
    except GuardrailViolationError as gv:
        sys.stderr.write(f"Guardrail Violation: {gv}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
