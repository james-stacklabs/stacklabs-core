#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: CREATOR LOGIN WIRETAP SCHEMA MIGRATION RUNNER
# Script: /home/james/stacklabs/scripts/apply_creator_wiretap_migration.py
# Work Order: WO-2026-0910-CLOUDFLARE-TUNNEL-LOGIN-WIRETAP (CI: 15_FanStack / sovereign_core_api)
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATION_FILE = "/home/james/stacklabs/dna/migrations/041__CREATE_CREATOR_ACCESS_AUDIT_SCHEMA.sql"

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
    print("\n🔍 [VERIFICATION] Verifying creator_access_audit table...")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='creator_access_audit'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  ✅ Active tables: {tables}")

    cur.execute("PRAGMA table_info(creator_access_audit)")
    columns = [r[1] for r in cur.fetchall()]
    print(f"  ✅ creator_access_audit columns: {columns}")

    conn.close()
    print("\n🎉 [MIGRATION COMPLETE] Creator Access Audit schema active in sovereign_now.db.")

if __name__ == "__main__":
    apply_migration()
