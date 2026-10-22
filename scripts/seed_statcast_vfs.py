#!/usr/bin/env python3
"""
scripts/seed_statcast_vfs.py
Proof of Concept: Statcast Player Split Topology in /dev/shm/vfs/sports
Author: James Carroll (Pilot) & Cockpit Architect
Target: /dev/shm/vfs/sports/mlb
Invariants: 0, 15, 32, 35
"""
import time
from pathlib import Path

VFS_SPORTS = Path("/dev/shm/vfs/sports/mlb")

def stage_alonso_topology():
    # Setup directories
    alonso = VFS_SPORTS / "players" / "alonso_pete"
    (alonso / "splits" / "vs_rhp").mkdir(parents=True, exist_ok=True)
    (alonso / "splits" / "vs_lhp").mkdir(parents=True, exist_ok=True)
    (alonso / "pitch_types" / "slider").mkdir(parents=True, exist_ok=True)
    (alonso / "pitch_types" / "four_seam").mkdir(parents=True, exist_ok=True)

    # Populate Alonso Scalars
    (alonso / "splits" / "vs_rhp" / "woba.txt").write_text("0.344\n")
    (alonso / "splits" / "vs_rhp" / "slg.txt").write_text("0.504\n")
    (alonso / "splits" / "vs_lhp" / "woba.txt").write_text("0.388\n")
    (alonso / "splits" / "vs_lhp" / "slg.txt").write_text("0.540\n")
    
    (alonso / "pitch_types" / "slider" / "chase_pct.txt").write_text("32.1\n")
    (alonso / "pitch_types" / "slider" / "whiff_pct.txt").write_text("36.8\n")
    (alonso / "pitch_types" / "four_seam" / "xwoba.txt").write_text("0.410\n")

    # Setup Active Game Matchup
    at_bat = VFS_SPORTS / "games" / "nym_phi_live" / "at_bat"
    at_bat.mkdir(parents=True, exist_ok=True)
    
    # Symlink batter
    batter_link = at_bat / "batter"
    if batter_link.exists() or batter_link.is_symlink():
        batter_link.unlink()
    batter_link.symlink_to("../../../players/alonso_pete")

def benchmark_statcast_read():
    at_bat = VFS_SPORTS / "games" / "nym_phi_live" / "at_bat"
    
    # Benchmark: Resolve batter symlink and pull LHP split + Slider chase %
    t0 = time.perf_counter_ns()
    
    batter_dir = (at_bat / "batter").resolve()
    lhp_woba = (batter_dir / "splits" / "vs_lhp" / "woba.txt").read_text().strip()
    slider_chase = (batter_dir / "pitch_types" / "slider" / "chase_pct.txt").read_text().strip()
    
    elapsed_us = (time.perf_counter_ns() - t0) / 1000.0
    payload = f"LHP_wOBA: {lhp_woba} | Slider_Chase: {slider_chase}%"

    print("==================================================================")
    print("⚡ STACKLABS STATCAST VFS CMDB BENCHMARK (CLIO METAL)")
    print("==================================================================")
    print(f"Traversal & Read Latency: {elapsed_us:.2f} microseconds")
    print(f"Ingested Context Payload: {len(payload.encode('utf-8'))} bytes (~6 tokens)")
    print(f"Resolved Data:            {payload}")
    print("==================================================================")

if __name__ == "__main__":
    stage_alonso_topology()
    benchmark_statcast_read()
