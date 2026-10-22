#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: SENTINEL HERD SIMULATION MIGRATION RUNNER
# Script: /home/james/stacklabs/scripts/apply_sentinel_simulation_migration.py
# Ticket: WO-2026-0907-SENTINEL-SIM (CI: 29_Sovereign_Sentinel)
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATION_FILE = "/home/james/stacklabs/dna/migrations/038__CREATE_SENTINEL_HERD_SIMULATION_SCHEMA.sql"

def apply_migration():
    print(f"🚀 [SCHEMA MIGRATION] Applying {MIGRATION_FILE} to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
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
    print("\n🔍 [VERIFICATION] Verifying sentinel tables...")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sentinel_%'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  ✅ Active sentinel tables: {tables}")

    cur.execute("SELECT count(*) FROM sentinel_animal")
    animal_count = cur.fetchone()[0]
    print(f"  ✅ Registered Longhorn Herd: {animal_count} animals")

    cur.execute("SELECT count(*) FROM sentinel_geofence")
    fence_count = cur.fetchone()[0]
    print(f"  ✅ Geofenced zones: {fence_count} zones")

    # Seed baseline telemetry for all 25 animals if empty
    cur.execute("SELECT count(*) FROM sentinel_telemetry")
    telem_count = cur.fetchone()[0]
    if telem_count == 0:
        print("\n🌱 [SEEDING] Generating initial telemetry coordinates for 25 Longhorns...")
        cur.execute("SELECT animal_id, tag_rfid, name, current_status FROM sentinel_animal")
        animals = cur.fetchall()
        import random
        # Base coordinates for Pasture A (North Grazing) around 33.8839° N, 84.5144° W
        # Screen coords map: x: 150-450, y: 80-280
        for a in animals:
            aid = a[0]
            lat = 33.8840 + (random.uniform(-0.002, 0.002))
            lon = -84.5140 + (random.uniform(-0.002, 0.002))
            vel = round(random.uniform(0.2, 1.8), 2)
            rum = random.randint(480, 560)
            temp = round(random.uniform(101.2, 102.2), 1)
            cur.execute("""
                INSERT INTO sentinel_telemetry (animal_id, latitude, longitude, velocity_mph, rumination_minutes_daily, core_temp_f)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (aid, lat, lon, vel, rum, temp))
        conn.commit()
        print("  ✅ Baseline telemetry frames seeded.")

    conn.close()
    print("\n🎉 [MIGRATION COMPLETE] Sentinel simulation schema active and ready.")

if __name__ == "__main__":
    apply_migration()
