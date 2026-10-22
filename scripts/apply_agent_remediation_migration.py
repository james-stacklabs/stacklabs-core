#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: AGENT REMEDIATION MEMORY SCHEMA MIGRATION RUNNER
# Script: /home/james/stacklabs/scripts/apply_agent_remediation_migration.py
# Ticket: STRY0824901-AGENT-REMEDIATION-REFLEX-CACHE
# CI: sovereign_knot_core
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATION_FILE = "/home/james/stacklabs/dna/migrations/053__CREATE_AGENT_REMEDIATION_MEMORY_LEDGER.sql"
EXECUTED_DIR = "/home/james/stacklabs/dna/migrations/executed"

def apply_migration():
    print(f"🚀 [SCHEMA MIGRATION] Applying {MIGRATION_FILE} to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=30000;")
    cur = conn.cursor()

    with open(MIGRATION_FILE, "r") as f:
        sql_commands = f.read()

    # Strip comments line by line
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
            print(f"  ❌ Error executing statement: {stmt}\n  Error: {e}")
            conn.rollback()
            conn.close()
            sys.exit(1)

    conn.commit()
    conn.close()
    print("✨ [SCHEMA MIGRATION] Migration 053 completed successfully!")

    # Record copy in executed directory
    os.makedirs(EXECUTED_DIR, exist_ok=True)
    target = os.path.join(EXECUTED_DIR, os.path.basename(MIGRATION_FILE))
    with open(target, "w") as f:
        f.write(sql_commands)
    print(f"📁 Archived ledger in {target}")

if __name__ == "__main__":
    apply_migration()
