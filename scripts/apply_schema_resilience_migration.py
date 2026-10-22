#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: SCHEMA RESILIENCE MIGRATION RUNNER
# Script: /home/james/stacklabs/scripts/apply_schema_resilience_migration.py
# SDLC: ENHC2026082202
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATION_FILE = "/home/james/stacklabs/dna/migrations/20260822_schema_resilience_column_aliases.sql"

def apply_migration():
    print(f"🚀 [SCHEMA MIGRATION] Applying {MIGRATION_FILE} to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    with open(MIGRATION_FILE, "r") as f:
        sql_commands = f.read()

    # Strip comments line by line first
    clean_lines = []
    for line in sql_commands.splitlines():
        trimmed = line.strip()
        if not trimmed.startswith("--"):
            clean_lines.append(line)
    clean_sql = "\n".join(clean_lines)

    for statement in clean_sql.split(";"):
        stmt = statement.strip()
        if not stmt:
            continue
        try:
            cur.execute(stmt)
            print(f"  ✓ Executed: {stmt[:60]}...")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"  ℹ️ Column already exists: {stmt[:60]}")
            else:
                print(f"  ⚠️ Warning on statement: {stmt[:60]} -> {e}")

    conn.commit()

    # Assertions & Verification
    print("\n🔍 [VERIFICATION] Verifying column presence...")
    cur.execute("PRAGMA table_info(persona)")
    persona_cols = [c[1] for c in cur.fetchall()]
    assert "name" in persona_cols, "persona.name column missing!"
    print("  ✅ persona.name column verified.")

    cur.execute("PRAGMA table_info(sport_schedule)")
    schedule_cols = [c[1] for c in cur.fetchall()]
    for col in ["home_team_name", "away_team_name", "home_score", "away_score", "current_status"]:
        assert col in schedule_cols, f"sport_schedule.{col} column missing!"
        print(f"  ✅ sport_schedule.{col} column verified.")

    # Test Query
    cur.execute("SELECT name, user_name, team FROM persona LIMIT 3")
    print("\n📋 Sample persona query using 'name':", cur.fetchall())

    cur.execute("SELECT game_pk, home_team_name, away_team_name, home_score, away_score FROM sport_schedule WHERE sport = 'NFL' LIMIT 3")
    print("📋 Sample sport_schedule query using 'home_team_name':", cur.fetchall())

    conn.close()
    print("\n🎉 [MIGRATION COMPLETE] All schema resilience columns active and verified!")

if __name__ == "__main__":
    apply_migration()
