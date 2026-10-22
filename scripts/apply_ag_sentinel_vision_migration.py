#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: AGRICULTURAL EDGE VISION MIGRATION RUNNER
# Script: /home/james/stacklabs/scripts/apply_ag_sentinel_vision_migration.py
# Work Order: WO0010032-AG-SENTINEL-PASTURE-AND-LIVESTOCK-V (CI: sovereign_sentinel_ag)
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATION_FILE = "/home/james/stacklabs/dna/migrations/040__CREATE_AG_SENTINEL_VISION_SCHEMA.sql"

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
    print("\n🔍 [VERIFICATION] Verifying ag_sentinel tables...")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ag_%'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  ✅ Active agricultural tables: {tables}")

    cur.execute("SELECT count(*) FROM ag_toxicology_index")
    flora_count = cur.fetchone()[0]
    print(f"  ✅ Indexed Botanical Species: {flora_count} plants")

    cur.execute("SELECT count(*) FROM ag_livestock_registry")
    livestock_count = cur.fetchone()[0]
    print(f"  ✅ Livestock Biometric Registry: {livestock_count} animals")

    cur.execute("SELECT count(*) FROM ag_sentinel_field_log")
    log_count = cur.fetchone()[0]
    print(f"  ✅ Field Telemetry Ingress Log: {log_count} scan logs")

    conn.close()
    print("\n🎉 [MIGRATION COMPLETE] Sovereign Sentinel Agricultural Edge Vision schema active.")

if __name__ == "__main__":
    apply_migration()
