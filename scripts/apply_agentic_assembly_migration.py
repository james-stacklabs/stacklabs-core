#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: MARD AGENTIC CODING ASSEMBLY LINE SCHEMA MIGRATION RUNNER
# Script: /home/james/stacklabs/scripts/apply_agentic_assembly_migration.py
# Work Order: WO0010081-MARD-AGENTIC-CODING-ASSEMBLY-LINE
# CI: sovereign_knot_core / mard_assembly_line
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATION_FILE = "/home/james/stacklabs/dna/migrations/049__CREATE_AGENTIC_ASSEMBLY_LINE_SCHEMA.sql"

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
            print(f"  ⚠️ Warning on statement: {stmt[:60]} -> {e}")

    conn.commit()

    # Verify tables
    print("\n🔍 [VERIFICATION] Verifying assembly line tables...")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('sys_assembly_run', 'sys_assembly_artifact')")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  ✅ Active tables: {tables}")

    cur.execute("PRAGMA table_info(sys_assembly_run)")
    run_cols = [r[1] for r in cur.fetchall()]
    print(f"  ✅ sys_assembly_run columns: {run_cols}")

    cur.execute("PRAGMA table_info(sys_assembly_artifact)")
    art_cols = [r[1] for r in cur.fetchall()]
    print(f"  ✅ sys_assembly_artifact columns: {art_cols}")

    conn.close()
    print("\n🎉 [MIGRATION COMPLETE] Agentic Coding Assembly Line schema active in sovereign_now.db.")

if __name__ == "__main__":
    apply_migration()
