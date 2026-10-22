#!/usr/bin/env python3
"""
StackLabs Hardened Dual-Plane VFS: Cold-Boot Restoration Engine
Path: /home/james/stacklabs/scripts/vfs_cold_boot_restore.py
Author: James Carroll (Pilot) & Cockpit Architect
"""
import sys
import shutil
import time
import sqlite3
from pathlib import Path

# Defensive path resolution
sys.path.insert(0, str(Path(__file__).parent))

from vfs_demand_pager import VFSDemandPager

DB_PATH = Path("/home/james/stacklabs/vfs/cmdb.db")
VFS_SHM_ROOT = Path("/dev/shm/vfs")

def execute_cold_boot_restore():
    """
    Simulates a total machine reboot:
    1. Completely purges volatile /dev/shm/vfs.
    2. Reads active tickets from local NVMe SQLite WAL master.
    3. Re-materializes sparse working set in /dev/shm in < 500 ms.
    Zero WAN REST calls required.
    """
    print("[1/3] Simulating cold boot: wiping volatile /dev/shm/vfs...")
    if VFS_SHM_ROOT.exists():
        shutil.rmtree(VFS_SHM_ROOT)
    VFS_SHM_ROOT.mkdir(parents=True, exist_ok=True)

    print("[2/3] Reading active working sets from local NVMe SQLite WAL...")
    t0 = time.perf_counter_ns()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Find all open tickets
    cur.execute("SELECT number FROM tickets WHERE state NOT IN ('6', '7', 'RESOLVED', 'CLOSED');")
    open_tickets = [row["number"] for row in cur.fetchall()]
    conn.close()

    print(f"      Identified {len(open_tickets)} active open incidents to restore.")

    pager = VFSDemandPager(db_path=DB_PATH, vfs_root=VFS_SHM_ROOT)
    restored_count = 0
    total_ci_count = 0

    print("[3/3] Materializing active working sets into /dev/shm/vfs...")
    for ticket_num in open_tickets:
        res = pager.materialize_incident_working_set(ticket_num)
        restored_count += 1
        total_ci_count += res["ci_count"]

    elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

    return {
        "status": "RESTORED",
        "open_tickets": open_tickets,
        "restored_tickets": restored_count,
        "total_active_cis": total_ci_count,
        "elapsed_ms": round(elapsed_ms, 3)
    }

if __name__ == "__main__":
    res = execute_cold_boot_restore()
    print(f"[DONE] Cold-Boot Restoration Completed in {res['elapsed_ms']} ms!")
    print(f"       Active Incidents: {res['restored_tickets']} | Working Set CIs: {res['total_active_cis']}")
    print(f"       Recovery Status: Fully Operational (Zero WAN calls made).")
