#!/usr/bin/env python3
"""
scripts/faas_gameday_monitor.py
Unified Live Telemetry HUD & Benchmark Snapshot Logger for Clio Metal
Author: James Carroll (Pilot) & Cockpit Architect
Target: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
Invariants: 0, 15, 32, 35
"""
import os
import sys
import time
import json
import random
import select
from pathlib import Path
from datetime import datetime

VFS_ROOT = Path("/dev/shm/vfs")
LOG_DIR = Path("/home/james/stacklabs/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def check_stdin():
    """Non-blocking check for keypress."""
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1)
    return None

def save_benchmark_snapshot(cycle, read_times, cfb_state, mlb_state):
    """Saves an audited JSON benchmark receipt to disk."""
    if not read_times:
        return None, 0.0
        
    sorted_times = sorted(read_times)
    n = len(sorted_times)
    p50 = sorted_times[n // 2]
    p95 = sorted_times[min(int(n * 0.95), n - 1)]
    p99 = sorted_times[min(int(n * 0.99), n - 1)]
    avg_us = sum(read_times) / n

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "cycle_count": cycle,
        "sample_window_size": n,
        "latency_microseconds": {
            "mean": round(avg_us, 2),
            "p50_median": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "min": round(sorted_times[0], 2),
            "max": round(sorted_times[-1], 2)
        },
        "throughput_traversals_per_sec": int(1_000_000 / avg_us) if avg_us > 0 else 0,
        "active_cfb_state": cfb_state,
        "active_mlb_state": mlb_state,
        "host": "Clio (AMD Ryzen 7 7735HS, DDR5-4800, NVMe PCIe 4.0)"
    }

    filename = LOG_DIR / f"benchmark_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filename.write_text(json.dumps(snapshot, indent=2))
    return filename, avg_us

def run_monitor():
    os.system("clear")
    is_tty = sys.stdin.isatty()
    old_settings = None
    fd = None

    if is_tty:
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

    print("\033[1;36m========================================================================================\033[0m")
    print("\033[1;32m⚡ STACKLABS FAAS DUAL-SPORT REFLEX HUD & BENCHMARK LOGGER (CLIO METAL)\033[0m")
    print("\033[1;36m========================================================================================\033[0m")
    if is_tty:
        print("Press \033[1;33m[s]\033[0m to save benchmark snapshot receipt | Press \033[1;31m[q]\033[0m to quit.\n")
    else:
        print("Running in headless display mode (stdin is not a tty).\n")

    cycle = 0
    read_times = []

    try:
        if is_tty:
            import tty
            tty.setcbreak(fd)

        while True:
            cycle += 1

            # -------------------------------------------------------------
            # 1. EMULATE INGRESS WRITE (Simulating Real-Time Field Telemetry)
            # -------------------------------------------------------------
            bp = random.randint(78, 96)
            eps = random.randint(110, 260)
            clock = max(1, 15 - (cycle % 15))
            drift = round(-1.0 - (random.random() * 1.5), 1)

            (VFS_ROOT / "cfb" / "blood_pressure" / "current_pct.txt").write_text(f"{bp}\n")
            (VFS_ROOT / "cfb" / "chaos_center" / "velocity_eps.txt").write_text(f"{eps}\n")
            (VFS_ROOT / "mlb" / "games" / "live_game" / "at_bat" / "pitch_clock_sec.txt").write_text(f"{clock:02d}\n")
            (VFS_ROOT / "mlb" / "players" / "diaz_edwin" / "fatigue" / "release_z_drift_in.txt").write_text(f"{drift}\n")

            # -------------------------------------------------------------
            # 2. MEASURE MULTI-SPORT REFLEX TRAVERSAL (THE MICROSECOND READ)
            # -------------------------------------------------------------
            t0 = time.perf_counter_ns()

            # CFB Traversal: 3 files + 1 symlink
            cfb_down = (VFS_ROOT / "cfb" / "games" / "uga_vs_bama" / "down_and_dist.txt").read_text().strip()
            cfb_bp = (VFS_ROOT / "cfb" / "blood_pressure" / "current_pct.txt").read_text().strip()
            cfb_eps = (VFS_ROOT / "cfb" / "chaos_center" / "velocity_eps.txt").read_text().strip()
            cfb_timeouts = (VFS_ROOT / "cfb" / "games" / "uga_vs_bama" / "possession" / "timeouts.txt").read_text().strip()

            # MLB Traversal: 2 files + 2 symlinks + deep split reads
            at_bat = VFS_ROOT / "mlb" / "games" / "live_game" / "at_bat"
            mlb_count = (at_bat / "count.txt").read_text().strip()
            mlb_clock = (at_bat / "pitch_clock_sec.txt").read_text().strip()
            
            batter_dir = (at_bat / "batter").resolve()
            lhp_woba = (batter_dir / "splits" / "vs_lhp" / "woba.txt").read_text().strip()

            pitcher_dir = (at_bat / "pitcher").resolve()
            arm_drift = (pitcher_dir / "fatigue" / "release_z_drift_in.txt").read_text().strip()

            t_elapsed_us = (time.perf_counter_ns() - t0) / 1000.0
            read_times.append(t_elapsed_us)
            if len(read_times) > 100:
                read_times.pop(0)

            # -------------------------------------------------------------
            # 3. RENDER TERMINAL HUD
            # -------------------------------------------------------------
            if cycle % 5 == 0:
                avg_us = sum(read_times) / len(read_times)
                cfb_summary = f"{cfb_down} | BP: {cfb_bp}% | Chat: {cfb_eps}/s | TO: {cfb_timeouts}"
                mlb_summary = f"Cnt: {mlb_count} ({mlb_clock}s) | Alonso LHP: {lhp_woba} | ArmDrift: {arm_drift}\""

                sys.stdout.write(
                    f"\r\033[K[\033[1;33m{cycle:05d}\033[0m] "
                    f"\033[1;34mCFB:\033[0m {cfb_summary} | "
                    f"\033[1;35mMLB:\033[0m {mlb_summary} | "
                    f"\033[1;32m{avg_us:.2f} µs\033[0m"
                )
                sys.stdout.flush()

            # -------------------------------------------------------------
            # 4. HANDLE KEYPRESSES
            # -------------------------------------------------------------
            if is_tty:
                ch = check_stdin()
                if ch == 's':
                    cfb_snapshot_state = {"down": cfb_down, "bp": cfb_bp, "eps": cfb_eps, "timeouts": cfb_timeouts}
                    mlb_snapshot_state = {"count": mlb_count, "clock": mlb_clock, "lhp_woba": lhp_woba, "arm_drift": arm_drift}
                    snap_path, snap_lat = save_benchmark_snapshot(cycle, read_times, cfb_snapshot_state, mlb_snapshot_state)
                    if snap_path:
                        sys.stdout.write(f"\n\033[1;32m[RECEIPT SAVED]\033[0m {snap_path.name} (Latency: {snap_lat:.2f} µs)\n")
                        sys.stdout.flush()
                elif ch == 'q':
                    break

            time.sleep(0.05)  # 20 Hz loop

    finally:
        if is_tty and old_settings is not None:
            import termios
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("\n\n[DONE] Monitor stopped cleanly.")

if __name__ == "__main__":
    if not (VFS_ROOT / "cfb").exists():
        print("[!] VFS not seeded. Running seeder first...")
        import subprocess
        subprocess.run([sys.executable, str(Path(__file__).parent / "seed_gameday_vfs.py")], check=True)
    run_monitor()
