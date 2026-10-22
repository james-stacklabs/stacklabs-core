#!/usr/bin/env python3
"""
Benchmark the Saturday Turf Play VFS on Clio (/dev/shm/vfs/turf)
Path: /home/james/stacklabs/scripts/benchmark_turf.py
Author: James Carroll (Pilot) & Cockpit Architect
Target: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
"""
import os
import sys
import json
import time
from pathlib import Path

TURF_ROOT = Path("/dev/shm/vfs/turf")
LOG_PATH = Path("/home/james/stacklabs/logs/turf_reflex_benchmark.json")

def benchmark_turf_reflex():
    p_cond = os.fsencode(TURF_ROOT / "track" / "condition.txt")
    p_pace = os.fsencode(TURF_ROOT / "race_08" / "pace_scenario.txt")
    p_horse = TURF_ROOT / "race_08" / "posts" / "post_03"
    p_speed = os.fsencode(p_horse / "beyer_speed_last.txt")
    p_odds = os.fsencode(p_horse / "live_odds.txt")
    p_fair = os.fsencode(p_horse / "fair_odds.txt")
    p_jockey = os.fsencode(p_horse / "jockey" / "win_pct.txt")

    targets = [p_cond, p_pace, p_speed, p_odds, p_fair, p_jockey]

    # Warm up dentry cache across all targets
    for p in targets:
        fd = os.open(p, os.O_RDONLY)
        os.read(fd, 64)
        os.close(fd)

    runs = []
    last_vals = []
    for _ in range(10):
        t0 = time.perf_counter_ns()
        vals = []
        for p in targets:
            fd = os.open(p, os.O_RDONLY)
            vals.append(os.read(fd, 32).decode("utf-8").strip())
            os.close(fd)
        t1 = time.perf_counter_ns()
        runs.append((t1 - t0) / 1000.0)
        last_vals = vals

    avg_us = round(sum(runs) / len(runs), 2)
    min_us = round(min(runs), 2)
    track_cond, pace, speed, odds, fair_odds, jockey_win = last_vals
    payload = f"{track_cond} {pace} {speed} {odds} {fair_odds} {jockey_win}"
    payload_bytes = len(payload.encode('utf-8'))
    est_tokens = max(1, payload_bytes // 4)

    # Cloud Claude Baseline
    claude_ingest_tokens = 5000
    claude_latency_ms = 7500.0 # 7.5 seconds
    local_latency_ms = avg_us / 1000.0
    speedup = round((claude_latency_ms * 1000.0) / max(avg_us, 0.001), 1)
    token_savings_pct = round((1.0 - (est_tokens / claude_ingest_tokens)) * 100, 2)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_node": "clio (Beelink SER Mini PC, AMD Ryzen 7 7735HS, NVMe PCIe 4.0)",
        "domain": "Retina Pillar 04 / Saturday Turf Play",
        "benchmark": {
            "vfs_resolution_avg_us": avg_us,
            "vfs_resolution_min_us": min_us,
            "payload_bytes": payload_bytes,
            "est_tokens": est_tokens,
            "resolved_state": payload,
            "claude_cloud_baseline_ms": claude_latency_ms,
            "claude_tokens": claude_ingest_tokens,
            "speedup_factor": f"{speedup}x",
            "token_savings_pct": token_savings_pct,
            "pass": avg_us < 50.0
        }
    }

    print(f"--- SATURDAY TURF REFLEX BENCHMARK ---")
    print(f"Resolution Latency: {avg_us:.2f} µs (Min: {min_us:.2f} µs)")
    print(f"Payload Bytes:      {payload_bytes} bytes (~{est_tokens} tokens)")
    print(f"Resolved State:     {payload}")
    print(f"Claude Cloud Time:  {claude_latency_ms} ms (~{claude_ingest_tokens} tokens)")
    print(f"Reflex Speedup:     {speedup}x faster ({token_savings_pct}% fewer tokens)")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(report, indent=2))
    print(f"[+] Timing ledger locked to {LOG_PATH}")
    return report

if __name__ == "__main__":
    benchmark_turf_reflex()
