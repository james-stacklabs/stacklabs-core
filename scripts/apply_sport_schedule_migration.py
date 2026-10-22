#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: SPORT SCHEDULE MIGRATION RUNNER
# Script: /home/james/stacklabs/scripts/apply_sport_schedule_migration.py
# SDLC: ENHC2026082002
# Invariant: KI-038 & KI-029 (Prove It Works Doctrine)
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATION_SQL_PATH = "/home/james/stacklabs/dna/migrations/20260820_sport_schedule_migration.sql"

def run_migration():
    print(f"🚀 [MIGRATION ENHC2026082002] Starting sport_schedule schema transformation...")
    
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at canonical path: {DB_PATH}")
    if not os.path.exists(MIGRATION_SQL_PATH):
        raise FileNotFoundError(f"Migration script not found at: {MIGRATION_SQL_PATH}")

    with open(MIGRATION_SQL_PATH, "r") as f:
        sql_script = f.read()

    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    
    try:
        # Check if already migrated
        cur = conn.cursor()
        cur.execute("SELECT type, name FROM sqlite_master WHERE name IN ('sport_schedule', 'mlb_schedule', 'nfl_schedule');")
        existing = {row[1]: row[0] for row in cur.fetchall()}
        
        if existing.get('sport_schedule') == 'table' and existing.get('mlb_schedule') == 'view':
            print("ℹ️ Schema already at target state (sport_schedule table + mlb_schedule view). Running verification...")
        else:
            print("📦 Applying SQL migration script...")
            conn.executescript(sql_script)
            print("✅ SQL Migration executed successfully!")

        # Run Verification Assertions
        print("\n🧪 [VERIFICATION PASS]")
        
        # 1. Verify sport_schedule table
        cur.execute("SELECT sport, count(*) FROM sport_schedule GROUP BY sport;")
        counts = dict(cur.fetchall())
        print(f"  ✓ sport_schedule distribution: {counts}")
        assert counts.get('MLB', 0) > 0, "MLB games count must be > 0"
        
        # 2. Verify mlb_schedule VIEW
        cur.execute("SELECT count(*) FROM mlb_schedule;")
        mlb_count = cur.fetchone()[0]
        print(f"  ✓ mlb_schedule (VIEW) row count: {mlb_count}")
        assert mlb_count == counts.get('MLB', 0), f"mlb_schedule view count ({mlb_count}) must match MLB rows ({counts.get('MLB', 0)})"
        
        # 3. Verify nfl_schedule VIEW
        cur.execute("SELECT count(*) FROM nfl_schedule;")
        nfl_count = cur.fetchone()[0]
        print(f"  ✓ nfl_schedule (VIEW) row count: {nfl_count}")
        assert nfl_count == counts.get('NFL', 0), f"nfl_schedule view count ({nfl_count}) must match NFL rows ({counts.get('NFL', 0)})"
        
        # 4. Verify v_active_daily_slate VIEW
        cur.execute("SELECT count(*) FROM v_active_daily_slate;")
        active_count = cur.fetchone()[0]
        print(f"  ✓ v_active_daily_slate (VIEW) row count: {active_count}")
        
        # 5. Test INSTEAD OF INSERT trigger on mlb_schedule
        test_pk = "test_smoke_mlb_999999"
        cur.execute("DELETE FROM sport_schedule WHERE game_pk = ?", (test_pk,))
        cur.execute("""
            INSERT INTO mlb_schedule (game_pk, game_date, home_team, away_team, venue, status)
            VALUES (?, '2026-08-20', 'NYM', 'ATL', 'Citi Field', 'Scheduled')
        """, (test_pk,))
        cur.execute("SELECT sport FROM sport_schedule WHERE game_pk = ?", (test_pk,))
        res = cur.fetchone()
        assert res and res[0] == 'MLB', "Trigger failed to insert MLB sport discriminator"
        print(f"  ✓ INSTEAD OF INSERT on mlb_schedule validated (sport='{res[0]}')")
        
        # 6. Test INSTEAD OF UPDATE trigger on mlb_schedule
        cur.execute("UPDATE mlb_schedule SET status = 'Final' WHERE game_pk = ?", (test_pk,))
        cur.execute("SELECT status FROM sport_schedule WHERE game_pk = ?", (test_pk,))
        res_status = cur.fetchone()
        assert res_status and res_status[0] == 'Final', "Trigger failed to update status"
        print(f"  ✓ INSTEAD OF UPDATE on mlb_schedule validated (status='{res_status[0]}')")
        
        # 7. Clean up smoke test row
        cur.execute("DELETE FROM mlb_schedule WHERE game_pk = ?", (test_pk,))
        cur.execute("SELECT count(*) FROM sport_schedule WHERE game_pk = ?", (test_pk,))
        assert cur.fetchone()[0] == 0, "Trigger failed to delete row"
        print(f"  ✓ INSTEAD OF DELETE on mlb_schedule validated (cleaned up)")
        
        conn.commit()
        print("\n🎉 [SUCCESS] ENHC2026082002 Migration & Verification 100% Passed!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ [MIGRATION FAILURE] {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
