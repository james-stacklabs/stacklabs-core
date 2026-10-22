#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: TEST CMDB-GATED MANDO MAINTENANCE (ENHC2026082203)
# Script: /home/james/stacklabs/scripts/test_cmdb_mando_gating.py
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

# Import helper from mando_watchdog
sys.path.insert(0, "/home/james/stacklabs/scripts")
from mando_watchdog import is_ci_in_maintenance

def run_tests():
    print("🧪 [TEST SUITE] Starting CMDB-Gated Mando Maintenance Verification...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Test Hibernated Status (2)
    cur.execute("UPDATE cmdb_ci SET operational_status = 2 WHERE name = 'FanStackRelay';")
    conn.commit()
    is_maint = is_ci_in_maintenance("FanStackRelay")
    print(f"  [Test 1] FanStackRelay (status=2) in maintenance? -> {is_maint}")
    assert is_maint == True, "Expected is_ci_in_maintenance to return True for operational_status=2"

    # 2. Test Operational Status (1)
    cur.execute("UPDATE cmdb_ci SET operational_status = 1 WHERE name = 'FanStackRelay';")
    conn.commit()
    is_maint = is_ci_in_maintenance("FanStackRelay")
    print(f"  [Test 2] FanStackRelay (status=1) in maintenance? -> {is_maint}")
    assert is_maint == False, "Expected is_ci_in_maintenance to return False for operational_status=1"

    # 3. Test Core System CI (SovereignCore)
    is_core_maint = is_ci_in_maintenance("SovereignCore")
    print(f"  [Test 3] SovereignCore (Operational Core) in maintenance? -> {is_core_maint}")
    assert is_core_maint == False, "Expected SovereignCore to be active (not in maintenance)"

    # 4. Test Decommissioned Status (3)
    cur.execute("UPDATE cmdb_ci SET operational_status = 3 WHERE name = 'FanStackRelay';")
    conn.commit()
    is_maint_decom = is_ci_in_maintenance("FanStackRelay")
    print(f"  [Test 4] FanStackRelay (status=3 Retired) in maintenance? -> {is_maint_decom}")
    assert is_maint_decom == True, "Expected Retired CI to suppress monitoring"

    # 5. Set back to Hibernation (2) for the evening rest
    cur.execute("""
        UPDATE cmdb_ci 
        SET operational_status = 2, sys_updated_on = datetime('now')
        WHERE name IN ('FanStackRelay', 'MARDChatEngine', 'FanStackPoller', 'SovereignSports', 'FanStackPortal');
    """)
    conn.commit()
    conn.close()

    print("  [Test 5] FanStack CIs set to Maintenance/Hibernation (2) for evening shutdown.")
    for ci in ['FanStackRelay', 'MARDChatEngine', 'FanStackPoller', 'SovereignSports', 'FanStackPortal']:
        assert is_ci_in_maintenance(ci) == True, f"{ci} failed to enter maintenance mode!"

    print("\n🎉 [TEST SUITE PASS] 100% CMDB-gated maintenance checks verified successfully!")

if __name__ == "__main__":
    run_tests()
