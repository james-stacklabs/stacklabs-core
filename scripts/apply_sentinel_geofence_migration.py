#!/usr/bin/env python3
"""
Migration: Sentinel Dynamic Geofences (Tractive GPS Inspired)
Target Table: sentinel_geofence in /home/james/stacklabs/dna/sovereign_now.db
"""
import sys
import json
import datetime

if "/home/james/stacklabs" not in sys.path:
    sys.path.insert(0, "/home/james/stacklabs")

from scripts.core.db import get_db

def run_migration():
    print("[MIGRATION] Starting sentinel_geofence schema migration...")
    with get_db() as conn:
        cur = conn.cursor()
        
        # 1. Read existing rows if table exists
        existing_rows = []
        try:
            cur.execute("SELECT * FROM sentinel_geofence")
            existing_rows = [dict(r) for r in cur.fetchall()]
            print(f"[MIGRATION] Found {len(existing_rows)} existing geofences.")
        except Exception as e:
            print(f"[MIGRATION] Note checking existing table: {e}")

        # 2. Re-create sentinel_geofence table with new dynamic specification
        cur.execute("DROP TABLE IF EXISTS sentinel_geofence_backup;")
        try:
            cur.execute("CREATE TABLE sentinel_geofence_backup AS SELECT * FROM sentinel_geofence;")
        except Exception:
            pass
        cur.execute("DROP TABLE IF EXISTS sentinel_geofence;")
        
        create_sql = """
        CREATE TABLE IF NOT EXISTS sentinel_geofence (
          zone_id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          zone_type TEXT NOT NULL DEFAULT 'SAFE_ZONE', -- 'SAFE_ZONE', 'POWER_SAVING', 'DANGER_ZONE'
          polygon_geojson TEXT,
          hazard_level TEXT DEFAULT 'NOMINAL', -- 'NOMINAL', 'WATCH', 'CRITICAL'
          hazard_description TEXT,
          center_x REAL DEFAULT 500.0,
          center_y REAL DEFAULT 300.0,
          radius REAL DEFAULT 80.0,
          power_saving_mode INTEGER DEFAULT 0,
          alert_neighbors INTEGER DEFAULT 0,
          created_at TEXT NOT NULL
        );
        """
        cur.execute(create_sql)
        print("[MIGRATION] Created sentinel_geofence table with new dynamic schema.")

        # 3. Seed / restore default zones
        defaults = [
            {
                "zone_id": "zone_pasture_a",
                "name": "Pasture A - North Grazing",
                "zone_type": "SAFE_ZONE",
                "polygon_geojson": '{"type":"Polygon","coordinates":[[[150,80],[450,80],[450,280],[150,280],[150,80]]]}',
                "hazard_level": "NOMINAL",
                "hazard_description": "Optimal forage Bermuda grass. Main rotational pasture.",
                "center_x": 300.0,
                "center_y": 180.0,
                "radius": 120.0,
                "power_saving_mode": 0,
                "alert_neighbors": 0,
                "created_at": "2026-09-07 17:01:57"
            },
            {
                "zone_id": "zone_pasture_b",
                "name": "Pasture B - Timber Brush",
                "zone_type": "SAFE_ZONE",
                "polygon_geojson": '{"type":"Polygon","coordinates":[[[480,80],[850,80],[850,300],[480,300],[480,80]]]}',
                "hazard_level": "WATCH",
                "hazard_description": "Dense timber brush and perimeter fence line.",
                "center_x": 665.0,
                "center_y": 190.0,
                "radius": 130.0,
                "power_saving_mode": 0,
                "alert_neighbors": 0,
                "created_at": "2026-09-07 17:01:57"
            },
            {
                "zone_id": "zone_pasture_c",
                "name": "Pasture C - Creek Basin",
                "zone_type": "SAFE_ZONE",
                "polygon_geojson": '{"type":"Polygon","coordinates":[[[150,320],[520,320],[520,540],[150,540],[150,320]]]}',
                "hazard_level": "WATCH",
                "hazard_description": "Low-lying creek bed and natural drainage basin.",
                "center_x": 335.0,
                "center_y": 430.0,
                "radius": 130.0,
                "power_saving_mode": 0,
                "alert_neighbors": 0,
                "created_at": "2026-09-07 17:01:57"
            },
            {
                "zone_id": "zone_solar_tank",
                "name": "Solar Tank #2 Zone",
                "zone_type": "POWER_SAVING",
                "polygon_geojson": '{"type":"Polygon","coordinates":[[[430,260],[520,260],[520,340],[430,340],[430,260]]]}',
                "hazard_level": "NOMINAL",
                "hazard_description": "Ultrasonic water trough and solar pump station. LoRa Gateway dwell zone.",
                "center_x": 475.0,
                "center_y": 300.0,
                "radius": 60.0,
                "power_saving_mode": 1,
                "alert_neighbors": 0,
                "created_at": "2026-09-07 17:01:57"
            },
            {
                "zone_id": "zone_main_corral",
                "name": "Main Corral & Chute",
                "zone_type": "POWER_SAVING",
                "polygon_geojson": '{"type":"Polygon","coordinates":[[[560,340],[850,340],[850,540],[560,540],[560,340]]]}',
                "hazard_level": "NOMINAL",
                "hazard_description": "Holding pens and squeeze chute. Wi-Fi Base Station dwell zone.",
                "center_x": 705.0,
                "center_y": 440.0,
                "radius": 110.0,
                "power_saving_mode": 1,
                "alert_neighbors": 0,
                "created_at": "2026-09-07 17:01:57"
            }
        ]

        # Insert defaults or migrated rows
        for d in defaults:
            cur.execute("""
                INSERT INTO sentinel_geofence (
                    zone_id, name, zone_type, polygon_geojson, hazard_level,
                    hazard_description, center_x, center_y, radius,
                    power_saving_mode, alert_neighbors, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                d["zone_id"], d["name"], d["zone_type"], d["polygon_geojson"], d["hazard_level"],
                d["hazard_description"], d["center_x"], d["center_y"], d["radius"],
                d["power_saving_mode"], d["alert_neighbors"], d["created_at"]
            ))

        conn.commit()
        print(f"[MIGRATION] Successfully initialized {len(defaults)} geofence zones.")

if __name__ == "__main__":
    run_migration()
