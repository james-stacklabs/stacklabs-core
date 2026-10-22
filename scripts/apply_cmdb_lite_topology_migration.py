#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: CMDB LITE & HORIZON TOPOLOGY MIGRATION RUNNER
# Script: /home/james/stacklabs/scripts/apply_cmdb_lite_topology_migration.py
# Ticket: WO0010456
# CI: hw_clio
# ==============================================================================
import os
import sys
from pathlib import Path

# Ensure scripts dir in sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.db import get_db, DB_PATH

MIGRATION_FILE = "/home/james/stacklabs/dna/migrations/057__CMDB_LITE_AND_HORIZON_TOPOLOGY_ALIGNMENT.sql"
EXECUTED_DIR = "/home/james/stacklabs/dna/migrations/executed"


def apply_migration():
    print(f"🚀 [SCHEMA MIGRATION] Applying {MIGRATION_FILE} to {DB_PATH}...")

    with open(MIGRATION_FILE, "r") as f:
        sql_commands = f.read()

    # Clean lines
    clean_lines = []
    for line in sql_commands.splitlines():
        trimmed = line.strip()
        if not trimmed.startswith("--"):
            clean_lines.append(line)
    clean_sql = "\n".join(clean_lines)

    with get_db() as conn:
        cur = conn.cursor()
        for statement in clean_sql.split(";"):
            stmt = statement.strip()
            if not stmt or stmt.upper() in ("BEGIN TRANSACTION", "COMMIT"):
                continue
            try:
                cur.execute(stmt)
                print(f"  ✓ Executed: {stmt[:60].replace(chr(10), ' ')}...")
            except Exception as e:
                print(f"  ❌ Error executing statement: {stmt}\n  Error: {e}")
                conn.rollback()
                sys.exit(1)
        conn.commit()

    print("✨ [SCHEMA MIGRATION] Migration 057 applied successfully!")

    # Record copy in executed directory
    os.makedirs(EXECUTED_DIR, exist_ok=True)
    target = os.path.join(EXECUTED_DIR, os.path.basename(MIGRATION_FILE))
    with open(target, "w") as f:
        f.write(sql_commands)
    print(f"📁 Archived ledger in {target}")


if __name__ == "__main__":
    apply_migration()
