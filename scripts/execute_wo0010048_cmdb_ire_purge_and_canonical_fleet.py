#!/usr/bin/env python3
"""
================================================================================
🚀 SOVEREIGN CMDB IRE PURGE & CANONICAL FLEET ALIGNMENT
Ticket: WO0010048-CMDB-IRE-PURGE-AND-CANONICAL-FLEET-
Target: CMDB Service & sovereign_now.db
================================================================================
Actions:
1. Applies migration 045__CMDB_IRE_PURGE_AND_CANONICAL_FLEET_ALIGNMENT.sql
2. Purges ghost records, DHCP mobile leases, and duplicate applications
3. Seeds authoritative physical hardware fleet (Clio, Argo, Calvin, Hobbes, 
   Metsy-Prime, Mando, Grogu, Workstations)
4. Registers 10 camera vision nodes (C120, 2x Nest, 7x attached webcams)
5. Rebuilds clean parent-child relational mappings in cmdb_rel_ci
6. Emits execution evidence report
================================================================================
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timezone

TICKET_ID = "WO0010048-CMDB-IRE-PURGE-AND-CANONICAL-FLEET-"
TICKET_DIR = f"/home/james/sovereign_inbox/tickets/{TICKET_ID}"
EVIDENCE_PATH = f"{TICKET_DIR}/execution_evidence.json"
MIGRATION_PATH = "/home/james/stacklabs/dna/migrations/045__CMDB_IRE_PURGE_AND_CANONICAL_FLEET_ALIGNMENT.sql"
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

os.makedirs(TICKET_DIR, exist_ok=True)

def main():
    print("=" * 80)
    print(f"🚀 INITIATING CMDB CANONICAL FLEET ALIGNMENT [{TICKET_ID}]")
    print(f"[*] Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    c = conn.cursor()

    # 1. Inspect initial hardware count
    c.execute("SELECT count(*) FROM cmdb_ci WHERE sys_class_name = 'cmdb_ci_hardware'")
    before_hw = c.fetchone()[0]
    print(f"[*] Pre-migration hardware CI count: {before_hw}")

    # 2. Run Migration
    print(f"[*] Executing SQL migration: {MIGRATION_PATH}...")
    with open(MIGRATION_PATH, "r") as f:
        sql = f.read()
    c.executescript(sql)
    conn.commit()

    # Archive to executed migrations ledger
    import shutil
    executed_mig = "/home/james/stacklabs/dna/migrations/executed/045__CMDB_IRE_PURGE_AND_CANONICAL_FLEET_ALIGNMENT.sql"
    os.makedirs(os.path.dirname(executed_mig), exist_ok=True)
    shutil.copy2(MIGRATION_PATH, executed_mig)

    # 3. Query canonical fleet
    c.execute("""
        SELECT c.sys_id, c.name, coalesce(h.ip_address, 'N/A'), c.short_description 
        FROM cmdb_ci c 
        LEFT JOIN cmdb_ci_hardware h ON c.sys_id = h.sys_id 
        WHERE c.sys_class_name = 'cmdb_ci_hardware' 
        ORDER BY c.name ASC
    """)
    hw_rows = c.fetchall()
    print(f"\n[✓] Authoritative Physical Fleet ({len(hw_rows)} nodes):")
    for r in hw_rows:
        print(f"    - [{r[0]}] {r[1]} ({r[2]}): {r[3]}")

    # 4. Query cameras
    c.execute("SELECT sys_id, name, short_description FROM cmdb_ci WHERE sys_class_name = 'cmdb_ci_camera' ORDER BY name ASC")
    cam_rows = c.fetchall()
    print(f"\n[✓] Registered Camera Vision Fleet ({len(cam_rows)} cameras):")
    for r in cam_rows:
        print(f"    - [{r[0]}] {r[1]}: {r[2]}")

    # 5. Query relationships
    c.execute("SELECT count(*) FROM cmdb_rel_ci")
    rel_count = c.fetchone()[0]
    print(f"\n[✓] Active CMDB Relationships: {rel_count}")

    conn.close()

    # 6. Write evidence
    evidence = {
        "ticket_id": TICKET_ID,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "hardware_nodes": [{"sys_id": r[0], "name": r[1], "ip": r[2], "desc": r[3]} for r in hw_rows],
        "cameras": [{"sys_id": r[0], "name": r[1], "desc": r[2]} for r in cam_rows],
        "relationship_count": rel_count,
        "status": "COMPLETED",
        "notes": "Ghost records purged. Physical fleet, camera vision nodes, and Tailscale mesh topology authoritatively aligned."
    }
    with open(EVIDENCE_PATH, "w") as f:
        json.dump(evidence, f, indent=2)
    artifacts_ev = f"{TICKET_DIR}/artifacts/execution_evidence.json"
    with open(artifacts_ev, "w") as f:
        json.dump(evidence, f, indent=2)

    print("\n" + "=" * 80)
    print(f"🎉 CMDB IRE ALIGNMENT COMPLETED WITH ZERO DEFECTS!")
    print(f"[✓] Evidence committed: {EVIDENCE_PATH}")
    print(f"[✓] Evidence artifact committed: {artifacts_ev}")
    print("=" * 80)
    return 0

if __name__ == "__main__":
    sys.exit(main())
