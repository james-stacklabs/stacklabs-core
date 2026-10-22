#!/usr/bin/env python3
"""
StackLabs Hardened Dual-Plane VFS: Comprehensive Adversarial Benchmark Suite
Path: /home/james/stacklabs/scripts/benchmark_hardened_dual_plane.py
Author: James Carroll (Pilot) & Cockpit Architect
"""
import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path

# Defensive path resolution
sys.path.insert(0, str(Path(__file__).parent))

from init_cmdb_sqlite_master import init_master_database, seed_master_data
from vfs_demand_pager import VFSDemandPager
from sn_outbox_worker import ServiceNowOutboxWorker
from vfs_cold_boot_restore import execute_cold_boot_restore

LOG_PATH = Path("/home/james/stacklabs/logs/wo0011024_hardened_dual_plane.json")
VFS_SHM = Path("/dev/shm/vfs")

def run_adversarial_suite():
    print("=" * 70)
    print("STACKLABS HARDENED DUAL-PLANE VFS: ADVERSARIAL BENCHMARK SUITE")
    print("=" * 70)

    # Clean volatile /dev/shm/vfs to isolate sparse hot cache measurements
    if VFS_SHM.exists():
        shutil.rmtree(VFS_SHM)
    VFS_SHM.mkdir(parents=True, exist_ok=True)

    # 1. Initialize & Seed Master Storage Plane
    conn = init_master_database()
    seed_master_data(conn)
    conn.close()

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_node": "clio (Beelink SER 7735HS, NVMe PCIe 4.0)",
        "benchmarks": {}
    }

    # -------------------------------------------------------------
    # TEST 1: The 4KB tmpfs Page Tax Elimination & RAM Audit
    # -------------------------------------------------------------
    print("\n--- TEST 1: Sparse Hot Cache RAM Footprint vs. Naive tmpfs ---")
    pager = VFSDemandPager()
    mat_res = pager.materialize_incident_working_set("INC0000060")
    ram_kb = mat_res["ram_footprint_kb"]
    
    # Naive math: 500,000 CIs * 5 files * 4KB = 10.24 GB + 4GB overhead = 14,200,000 KB
    naive_ram_kb = 14_200_000
    savings_pct = round((1.0 - (ram_kb / naive_ram_kb)) * 100, 4)

    print(f"  Sparse Working Set RAM: {ram_kb} KB ({ram_kb / 1024:.2f} MB)")
    print(f"  Naive tmpfs Projection: {naive_ram_kb / 1024 / 1024:.2f} GB")
    print(f"  RAM Reduction: {savings_pct}%")
    assert ram_kb < 5000, f"Sparse RAM footprint exceeded 5MB: {ram_kb} KB"
    
    report["benchmarks"]["ram_footprint"] = {
        "sparse_ram_kb": ram_kb,
        "naive_ram_projection_gb": 14.2,
        "ram_savings_pct": savings_pct,
        "pass": True
    }

    # -------------------------------------------------------------
    # TEST 2: Demand-Paging Latency
    # -------------------------------------------------------------
    print("\n--- TEST 2: Demand-Paging Subtree Materialization Latency ---")
    latencies = []
    for _ in range(5):
        m = pager.materialize_incident_working_set("INC0000060")
        latencies.append(m["elapsed_ms"])
    avg_latency = round(sum(latencies) / len(latencies), 3)
    print(f"  Average Materialization Latency: {avg_latency} ms across 5 runs.")
    assert avg_latency < 5.0, f"Materialization latency exceeded 5ms: {avg_latency} ms"

    report["benchmarks"]["demand_paging_latency"] = {
        "latencies_ms": latencies,
        "average_ms": avg_latency,
        "pass": avg_latency < 5.0
    }

    # -------------------------------------------------------------
    # TEST 3: Multi-Object ACID Transaction Arbiter
    # -------------------------------------------------------------
    print("\n--- TEST 3: Multi-Object ACID Transaction Arbiter ---")
    tx_res = pager.commit_multi_object_transaction(
        ci_id="sea-db-01",
        updates={"operational_status": "MAINTENANCE", "role": "FAILOVER_SECONDARY"},
        new_relationships=[("sea-db-01", "san-pure-01", "StandbyMirror")]
    )
    print(f"  Committed multi-object mutation in {tx_res['elapsed_ms']} ms.")
    # Verify in sparse VFS
    status_file = VFS_SHM / "cmdb" / "database" / "sea-db-01" / "operational" / "status.txt"
    vfs_status = status_file.read_text().strip() if status_file.exists() else "MISSING"
    print(f"  Verified Sparse VFS Status: {vfs_status}")
    assert vfs_status == "MAINTENANCE", f"VFS did not reflect atomic update: {vfs_status}"

    report["benchmarks"]["acid_transaction"] = {
        "elapsed_ms": tx_res["elapsed_ms"],
        "verified_vfs_state": vfs_status,
        "pass": vfs_status == "MAINTENANCE"
    }

    # -------------------------------------------------------------
    # TEST 4: Optimistic Concurrency Control (OCC) Split-Brain Prevention
    # -------------------------------------------------------------
    print("\n--- TEST 4: Optimistic Concurrency Control (OCC) Validation ---")
    worker = ServiceNowOutboxWorker(rate_limit=20.0) # Faster for benchmark
    
    # Enqueue remediation expecting sys_mod_count = 4
    outbox_id = worker.enqueue_remediation(
        ticket_number="INC0000060",
        action="PATCH_RESOLVE",
        payload={"state": "6", "resolution": "Remediated via Reflex"},
        expected_mod_count=4
    )
    # Simulate upstream human collision: human bumped sys_mod_count to 5
    conflict_drain = worker.drain_outbox(simulate_wan=True, simulated_mod_counts={"INC0000060": 5})
    conflict_detected = any(d["status"] == "CONFLICT" for d in conflict_drain)
    print(f"  Simulated Upstream Human Edit (sys_mod_count: 5 vs Expected: 4)")
    print(f"  Conflict Detection Triggered: {conflict_detected}")
    print(f"  Conflict Details: {conflict_drain[0].get('error')}")
    assert conflict_detected, "OCC failed to detect concurrent modification!"

    report["benchmarks"]["occ_split_brain_prevention"] = {
        "expected_mod_count": 4,
        "simulated_mod_count": 5,
        "conflict_detected": conflict_detected,
        "pass": conflict_detected
    }

    # -------------------------------------------------------------
    # TEST 5: Network Partition Durability & Outbox Token Bucket
    # -------------------------------------------------------------
    print("\n--- TEST 5: Network Partition Durability & Token-Bucket Drain ---")
    # Enqueue 5 items during simulated network partition (WAN down)
    enqueued_ids = []
    for i in range(5):
        eid = worker.enqueue_remediation(
            ticket_number=f"INC-TEST-{i:03d}",
            action="UPDATE",
            payload={"note": f"Partition test {i}"},
            expected_mod_count=1
        )
        enqueued_ids.append(eid)
    
    # Attempt drain with WAN offline
    offline_drain = worker.drain_outbox(simulate_wan=False)
    offline_buffered = all(d["status"] == "QUEUED_OFFLINE" for d in offline_drain)
    print(f"  WAN Offline: {len(offline_drain)} items safely buffered on NVMe SQLite WAL.")
    assert offline_buffered, "Items failed to buffer on NVMe during network partition!"

    # Restore WAN and drain with token bucket
    t_drain_start = time.perf_counter()
    online_drain = worker.drain_outbox(simulate_wan=True)
    drain_time = time.perf_counter() - t_drain_start
    online_completed = all(d["status"] == "COMPLETED" for d in online_drain)
    print(f"  WAN Restored: Drained {len(online_drain)} items via Token Bucket in {drain_time:.2f}s.")
    assert online_completed, "Outbox failed to drain cleanly when online!"

    report["benchmarks"]["network_partition_and_token_bucket"] = {
        "buffered_offline_count": len(offline_drain),
        "drained_online_count": len(online_drain),
        "drain_duration_seconds": round(drain_time, 3),
        "pass": offline_buffered and online_completed
    }

    # -------------------------------------------------------------
    # TEST 6: Cold-Boot Restoration Latency
    # -------------------------------------------------------------
    print("\n--- TEST 6: Cold-Boot Restoration from NVMe ---")
    boot_res = execute_cold_boot_restore()
    print(f"  Cold Boot Restore Elapsed: {boot_res['elapsed_ms']} ms.")
    print(f"  Restored Incidents: {boot_res['restored_tickets']} | Working Set CIs: {boot_res['total_active_cis']}")
    assert boot_res["elapsed_ms"] < 500.0, f"Cold boot restore exceeded 500ms: {boot_res['elapsed_ms']} ms"

    report["benchmarks"]["cold_boot_restore"] = {
        "elapsed_ms": boot_res["elapsed_ms"],
        "restored_incidents": boot_res["restored_tickets"],
        "working_set_cis": boot_res["total_active_cis"],
        "pass": boot_res["elapsed_ms"] < 500.0
    }

    # Write report
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(report, indent=2))
    print(f"\n[DONE] Benchmark report written to {LOG_PATH}")
    print("=" * 70)

if __name__ == "__main__":
    run_adversarial_suite()
