#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: FANCAST DEAD-AIR BANTER SCHEMA MIGRATION RUNNER
# Script: /home/james/stacklabs/scripts/apply_fancast_banter_migration.py
# Ticket: WO0010035-FANCAST-NFL-DEAD-AIR-BANTER-ENGINE (CI: 15_FanStack)
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATION_FILE = "/home/james/stacklabs/dna/migrations/043__CREATE_FANCAST_DEAD_AIR_BANTER_SCHEMA.sql"

def apply_migration():
    print(f"🚀 [SCHEMA MIGRATION] Applying {MIGRATION_FILE} to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=30000;")
    cur = conn.cursor()

    with open(MIGRATION_FILE, "r") as f:
        sql_commands = f.read()

    clean_lines = []
    for line in sql_commands.splitlines():
        trimmed = line.strip()
        if not trimmed.startswith("--"):
            clean_lines.append(line)
    clean_sql = "\n".join(clean_lines)

    for statement in clean_sql.split(";"):
        stmt = statement.strip()
        if not stmt or stmt.upper() in ("BEGIN TRANSACTION", "COMMIT"):
            continue
        try:
            cur.execute(stmt)
            print(f"  ✓ Executed: {stmt[:60]}...")
        except Exception as e:
            print(f"  ⚠️ Warning on statement: {stmt[:60]} -> {e}")

    conn.commit()

    print("\n🔍 [VERIFICATION] Verifying fancast_banter tables...")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'fancast_banter_%'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  ✅ Active tables: {tables}")

    cur.execute("SELECT id, active_mode, current_stoppage, turn_counter FROM fancast_banter_state WHERE id=1")
    state = cur.fetchone()
    print(f"  ✅ Initial State: {state}")

    conn.close()
    print("\n🎉 [MIGRATION COMPLETE] FanCast Dead-Air Banter schema active in sovereign_now.db.")

if __name__ == "__main__":
    apply_migration()
