#!/home/james/stacklabs/.venv/bin/python3
"""
Seed script for fanstack_unified_schedule table in SQLite WAL mode.
"""

import sqlite3
import pathlib

DB_PATH = pathlib.Path("/home/james/stacklabs/dna/fanstack_schedule.db")

CREATE_UNIFIED_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fanstack_unified_schedule (
    id TEXT PRIMARY KEY,
    raw_id TEXT NOT NULL,
    sport TEXT NOT NULL CHECK (sport IN ('mlb', 'nfl', 'cfb')),
    league TEXT NOT NULL CHECK (league IN ('MLB', 'NFL', 'CFB')),
    game_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('SCHEDULED', 'WARMUP', 'LIVE', 'FINAL', 'POSTPONED')),
    status_detail TEXT NOT NULL,
    clock_period INTEGER NOT NULL,
    clock_period_name TEXT NOT NULL,
    clock_display TEXT NOT NULL,
    clock_is_intermission INTEGER NOT NULL DEFAULT 0,
    away_code TEXT NOT NULL,
    away_full_name TEXT NOT NULL,
    away_score INTEGER NOT NULL DEFAULT 0,
    away_rank INTEGER,
    away_logo_url TEXT NOT NULL,
    home_code TEXT NOT NULL,
    home_full_name TEXT NOT NULL,
    home_score INTEGER NOT NULL DEFAULT 0,
    home_rank INTEGER,
    home_logo_url TEXT NOT NULL,
    odds_spread TEXT,
    odds_over_under REAL,
    odds_moneyline_away INTEGER,
    odds_moneyline_home INTEGER,
    venue_name TEXT NOT NULL,
    venue_city TEXT NOT NULL,
    venue_state TEXT NOT NULL,
    venue_roof TEXT NOT NULL CHECK (venue_roof IN ('open', 'dome', 'retractable')),
    venue_surface TEXT NOT NULL CHECK (venue_surface IN ('grass', 'turf')),
    venue_elevation_ft INTEGER NOT NULL DEFAULT 0,
    scheduled_start_iso TEXT NOT NULL,
    last_updated_iso TEXT NOT NULL,
    event_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fanstack_unified_sport_status
    ON fanstack_unified_schedule (sport, status, scheduled_start_iso);

CREATE INDEX IF NOT EXISTS idx_fanstack_unified_game_date
    ON fanstack_unified_schedule (game_date, sport);
"""

def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    # Check if an older schema without scheduled_start_iso exists and upgrade cleanly
    cur.execute("PRAGMA table_info(fanstack_unified_schedule);")
    cols = {row[1] for row in cur.fetchall()}
    if cols and "scheduled_start_iso" not in cols:
        cur.execute("DROP TABLE fanstack_unified_schedule;")
    conn.executescript(CREATE_UNIFIED_TABLE_SQL)
    conn.commit()
    conn.close()
    print(f"✔ SQLite WAL schedule database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
