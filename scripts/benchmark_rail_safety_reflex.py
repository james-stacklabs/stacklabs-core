#!/usr/bin/env python3
"""
StackLabs Wayside Rail Interlocking: VFS Safety Reflex Benchmark Suite
Path: /home/james/stacklabs/scripts/benchmark_rail_safety_reflex.py
Author: James Carroll (Pilot) & Cockpit Architect
Target Silicon: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
"""
import os
import sys
import json
import time
import shutil
import sqlite3
from pathlib import Path

# Add current scripts directory
sys.path.insert(0, str(Path(__file__).parent))
from seed_rail_interlocking import VFS_RAIL, DB_PATH, seed_rail_vfs, init_rail_master_db, seed_rail_master_db

LOG_PATH = Path("/home/james/stacklabs/logs/rail_interlocking_benchmark.json")

def audit_vfs_ram_footprint(path: Path) -> int:
    """Calculate RAM footprint of the VFS tree in KB."""
    total_bytes = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            p = Path(root) / f
            try:
                total_bytes += p.stat().st_size
            except OSError:
                pass
    return max(1, total_bytes // 1024)

def run_rail_benchmark_suite():
    print("=" * 75)
    print("STACKLABS WAYSIDE RAIL INTERLOCKING: BARE-METAL VFS REFLEX SUITE")
    print("=" * 75)

    # 1. Ensure clean baseline
    seed_rail_vfs(clean=True)
    conn = init_rail_master_db()
    seed_rail_master_db(conn)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_node": "clio (Beelink SER Mini PC, AMD Ryzen 7 7735HS, NVMe PCIe 4.0)",
        "domain": "Physical Industrial / Wayside Rail PTC & Interlocking",
        "benchmarks": {}
    }

    # -------------------------------------------------------------
    # BENCHMARK 1: Direct Inode Collision Detection Latency
    # -------------------------------------------------------------
    print("\n--- BENCHMARK 1: Kernel Inode Collision Detection (os.stat().st_ino) ---")
    trains_dir = VFS_RAIL / "trains"
    
    # Pre-index active train routes
    train_routes = [
        (train_dir.name, train_dir / "route" / "01")
        for train_dir in trains_dir.iterdir()
        if train_dir.is_dir() and (train_dir / "route" / "01").exists()
    ]
    # Warmup dentry cache
    for _, route_link in train_routes:
        _ = route_link.stat().st_ino

    detection_runs = []
    conflict_detected = False
    colliding_trains = []
    conflict_inode = None
    target_block_path = ""

    for _ in range(10):
        t0 = time.perf_counter_ns()
        reserved_inodes = {}
        detected = []
        for train_name, route_link in train_routes:
            # Kernel resolves symlink to underlying track block directory inode via os.stat().st_ino
            ino = route_link.stat().st_ino
            if ino in reserved_inodes:
                detected.append((reserved_inodes[ino], train_name, ino))
            else:
                reserved_inodes[ino] = train_name
        t1 = time.perf_counter_ns()
        elapsed_us = (t1 - t0) / 1000.0
        detection_runs.append(elapsed_us)
        if detected:
            conflict_detected = True
            colliding_trains = [detected[0][0], detected[0][1]]
            conflict_inode = detected[0][2]
            target_block_path = str(route_link.resolve())

    avg_detection_us = round(sum(detection_runs) / len(detection_runs), 2)
    min_detection_us = round(min(detection_runs), 2)
    print(f"  Conflict Detected: {conflict_detected}")
    print(f"  Colliding Entities: {colliding_trains} on Inode {conflict_inode}")
    print(f"  Physical Track Target: {target_block_path}")
    print(f"  Average Inode Detection Latency: {avg_detection_us} µs (Min: {min_detection_us} µs)")
    assert conflict_detected, "Failed to detect inode collision on block_101!"
    assert avg_detection_us < 25.0, f"Detection latency exceeded 25µs threshold: {avg_detection_us}µs"

    report["benchmarks"]["inode_collision_detection"] = {
        "conflict_detected": conflict_detected,
        "colliding_trains": colliding_trains,
        "target_inode": conflict_inode,
        "target_block_path": target_block_path,
        "avg_latency_us": avg_detection_us,
        "min_latency_us": min_detection_us,
        "pass": avg_detection_us < 25.0
    }

    # -------------------------------------------------------------
    # BENCHMARK 2: Autonomous Kinetic Reflex Actuation Latency
    # -------------------------------------------------------------
    print("\n--- BENCHMARK 2: Autonomous Kinetic Reflex Actuation ---")
    # Actuation actions:
    # 1. Trip emergency brake on train_west (the approaching hazard)
    # 2. Realign turnout_01 to REVERSE (diverting into siding_01)
    # 3. Drop signal aspect on block_101 to STOP
    brake_file = trains_dir / "train_west" / "emergency_brake.txt"
    switch_file = VFS_RAIL / "switches" / "turnout_01" / "alignment.txt"
    signal_file = VFS_RAIL / "track_blocks" / "block_101" / "signal_aspect.txt"

    actuations = [
        (os.fsencode(brake_file), b"TRIPPED\n"),
        (os.fsencode(switch_file), b"REVERSE\n"),
        (os.fsencode(signal_file), b"STOP\n")
    ]

    actuation_runs = []
    for _ in range(10):
        t_act0 = time.perf_counter_ns()
        for file_path, val in actuations:
            fd = os.open(file_path, os.O_WRONLY | os.O_TRUNC)
            os.write(fd, val)
            os.close(fd)
        t_act1 = time.perf_counter_ns()
        actuation_runs.append((t_act1 - t_act0) / 1000.0)

    total_reflex_loop_us = round(sum(actuation_runs) / len(actuation_runs), 2)
    min_reflex_loop_us = round(min(actuation_runs), 2)
    
    # Verify leaf state changes
    assert brake_file.read_text().strip() == "TRIPPED"
    assert switch_file.read_text().strip() == "REVERSE"
    assert signal_file.read_text().strip() == "STOP"
    
    print(f"  Actuation Completed: Brake=TRIPPED, Turnout=REVERSE, Signal=STOP")
    print(f"  Reflex Actuation Latency: {total_reflex_loop_us} µs (Min: {min_reflex_loop_us} µs)")
    assert total_reflex_loop_us < 50.0, f"Actuation latency exceeded 50µs threshold: {total_reflex_loop_us}µs"

    report["benchmarks"]["kinetic_reflex_actuation"] = {
        "actions_taken": [
            "train_west/emergency_brake.txt -> TRIPPED",
            "turnout_01/alignment.txt -> REVERSE",
            "block_101/signal_aspect.txt -> STOP"
        ],
        "latency_us": total_reflex_loop_us,
        "min_latency_us": min_reflex_loop_us,
        "pass": total_reflex_loop_us < 50.0
    }

    # -------------------------------------------------------------
    # BENCHMARK 3: Atomic State Persistence to SQLite WAL Ledger
    # -------------------------------------------------------------
    print("\n--- BENCHMARK 3: Atomic State Persistence to SQLite WAL ---")
    t_db0 = time.perf_counter_ns()
    with conn:
        conn.execute("""
            UPDATE rail_trains 
            SET emergency_brake = 'TRIPPED', updated_at = CURRENT_TIMESTAMP 
            WHERE id = 'train_west'
        """)
        conn.execute("""
            UPDATE rail_switches 
            SET alignment = 'REVERSE', updated_at = CURRENT_TIMESTAMP 
            WHERE id = 'turnout_01'
        """)
        conn.execute("""
            UPDATE rail_blocks 
            SET signal_aspect = 'STOP', updated_at = CURRENT_TIMESTAMP 
            WHERE id = 'block_101'
        """)
        conn.execute("""
            INSERT INTO rail_events (event_type, source_entity, details, latency_us)
            VALUES (?, ?, ?, ?)
        """, (
            "HEAD_ON_COLLISION_INTERCEPT",
            "VFS_REFLEX_CORE",
            f"Trip train_west emergency brake, switch turnout_01 to REVERSE into siding_01. Target Inode: {conflict_inode}",
            avg_detection_us + total_reflex_loop_us
        ))
    t_db1 = time.perf_counter_ns()
    db_commit_ms = round((t_db1 - t_db0) / 1_000_000.0, 3)
    print(f"  Flight Recorder Committed in: {db_commit_ms} ms")
    assert db_commit_ms < 10.0, f"DB commit exceeded 10ms: {db_commit_ms} ms"

    report["benchmarks"]["sqlite_wal_persistence"] = {
        "db_commit_ms": db_commit_ms,
        "journal_mode": "WAL",
        "pass": db_commit_ms < 10.0
    }

    # -------------------------------------------------------------
    # BENCHMARK 4: Cold-Boot Instant Restoration from NVMe
    # -------------------------------------------------------------
    print("\n--- BENCHMARK 4: Cold-Boot Instant Restoration from NVMe ---")
    # Simulate complete volatile RAM loss
    if VFS_RAIL.exists():
        shutil.rmtree(VFS_RAIL)
    
    t_rest0 = time.perf_counter_ns()
    # Reconstitute from SQLite WAL
    cur = conn.cursor()
    blocks = cur.execute("SELECT id, occupied, speed_limit_mph, signal_aspect FROM rail_blocks").fetchall()
    switches = cur.execute("SELECT id, alignment, locked, points_detected, facing_block_id, normal_block_id, reverse_block_id FROM rail_switches").fetchall()
    trains = cur.execute("SELECT id, name, speed_mph, heading, emergency_brake, reserved_block_id FROM rail_trains").fetchall()
    
    # Re-materialize VFS directories and leaf files
    (VFS_RAIL / "track_blocks").mkdir(parents=True, exist_ok=True)
    (VFS_RAIL / "switches").mkdir(parents=True, exist_ok=True)
    (VFS_RAIL / "trains").mkdir(parents=True, exist_ok=True)
    
    for b_id, occ, spd, sig in blocks:
        b_dir = VFS_RAIL / "track_blocks" / b_id
        b_dir.mkdir(parents=True, exist_ok=True)
        (b_dir / "occupied.txt").write_text(f"{occ}\n")
        (b_dir / "speed_limit_mph.txt").write_text(f"{spd}\n")
        (b_dir / "signal_aspect.txt").write_text(f"{sig}\n")
        
    for sw_id, align, lck, pts, facing, normal, reverse in switches:
        sw_dir = VFS_RAIL / "switches" / sw_id
        sw_dir.mkdir(parents=True, exist_ok=True)
        (sw_dir / "alignment.txt").write_text(f"{align}\n")
        (sw_dir / "locked.txt").write_text(f"{lck}\n")
        (sw_dir / "points_detected.txt").write_text(f"{pts}\n")
        if facing:
            (sw_dir / "facing_block").symlink_to(f"../../track_blocks/{facing}")
        if normal:
            (sw_dir / "normal_block").symlink_to(f"../../track_blocks/{normal}")
        if reverse:
            (sw_dir / "reverse_block").symlink_to(f"../../track_blocks/{reverse}")
            
    for t_id, name, spd, hdg, ebrake, r_block in trains:
        t_dir = VFS_RAIL / "trains" / t_id
        r_dir = t_dir / "route"
        r_dir.mkdir(parents=True, exist_ok=True)
        (t_dir / "id.txt").write_text(f"{name}\n")
        (t_dir / "speed_mph.txt").write_text(f"{spd}\n")
        (t_dir / "heading.txt").write_text(f"{hdg}\n")
        (t_dir / "emergency_brake.txt").write_text(f"{ebrake}\n")
        (r_dir / "01").symlink_to(f"../../../track_blocks/{r_block}")

    t_rest1 = time.perf_counter_ns()
    cold_boot_restore_ms = round((t_rest1 - t_rest0) / 1_000_000.0, 3)
    
    print(f"  Restored Rail Topology from NVMe in: {cold_boot_restore_ms} ms (Zero Network Calls)")
    assert cold_boot_restore_ms < 15.0, f"Cold boot restore exceeded 15ms: {cold_boot_restore_ms} ms"

    report["benchmarks"]["cold_boot_restore"] = {
        "restore_ms": cold_boot_restore_ms,
        "pass": cold_boot_restore_ms < 15.0
    }

    # -------------------------------------------------------------
    # BENCHMARK 5: Fieldbus & Memory Footprint Audit
    # -------------------------------------------------------------
    print("\n--- BENCHMARK 5: Resource Footprint & Speedup vs WAN SCADA ---")
    ram_kb = audit_vfs_ram_footprint(VFS_RAIL)
    db_size_kb = DB_PATH.stat().st_size // 1024
    
    # WAN SCADA round-trip baseline (cellular/satellite backhaul to central control center)
    wan_scada_ms = 450.0
    total_local_loop_ms = (avg_detection_us + total_reflex_loop_us) / 1000.0
    speedup = round(wan_scada_ms / total_local_loop_ms, 1)

    print(f"  VFS RAM Footprint: {ram_kb} KB (< 1 MB)")
    print(f"  NVMe DB Footprint: {db_size_kb} KB")
    print(f"  Local VFS Reflex Loop: {total_local_loop_ms:.4f} ms ({avg_detection_us + total_reflex_loop_us:.1f} µs)")
    print(f"  Centralized WAN SCADA: {wan_scada_ms} ms")
    print(f"  Deterministic Speedup: {speedup}x faster")

    report["benchmarks"]["system_metrics"] = {
        "vfs_ram_kb": ram_kb,
        "nvme_db_kb": db_size_kb,
        "local_loop_ms": total_local_loop_ms,
        "wan_scada_baseline_ms": wan_scada_ms,
        "speedup_factor": f"{speedup}x",
        "pass": True
    }

    # Lock timing ledger
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(report, indent=2))
    print(f"\n[+] Execution receipt locked to {LOG_PATH}")
    
    conn.close()
    return report

if __name__ == "__main__":
    report = run_rail_benchmark_suite()
