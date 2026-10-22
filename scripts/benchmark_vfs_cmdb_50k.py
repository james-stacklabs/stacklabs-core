#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs 50K CMDB Traversal Torture Benchmark
Path: /home/james/stacklabs/scripts/benchmark_vfs_cmdb_50k.py
Executes 100 randomized multi-hop upstream traversals across 50,000 CIs in /dev/shm
measuring microsecond resolution times and emitting empirical receipts.

Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Governing Spec: WO0011086
"""

import os
import sys
import json
import time
import random
import statistics
import logging
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cmdb_50k_benchmark")

CONCEPTS_DIR = Path("/dev/shm/vfs/cmdb_50k/ci")
RECEIPT_FILE = Path("/home/james/stacklabs/data/telemetry/cmdb_50k_benchmark_receipt.json")


def walk_upstream_root(start_node: str, max_depth: int = 10) -> Tuple[List[str], float]:
    path = [start_node]
    current = start_node
    depth = 0

    t_start = time.perf_counter_ns()

    while depth < max_depth:
        node_dir = CONCEPTS_DIR / current
        if not node_dir.exists():
            break

        # Look for reverse links indicating upstream dependencies/hosts
        next_hop = None
        for entry in os.scandir(node_dir):
            if entry.is_symlink() and entry.name.startswith("rev_"):
                try:
                    resolved = Path(os.path.realpath(entry.path)).name
                    if resolved not in path:
                        next_hop = resolved
                        break
                except OSError:
                    continue

        if not next_hop:
            break

        path.append(next_hop)
        current = next_hop
        depth += 1

    t_end = time.perf_counter_ns()
    duration_us = (t_end - t_start) / 1000.0
    return path, duration_us


def main():
    if not CONCEPTS_DIR.exists():
        logger.error(f"VFS concepts mount missing at {CONCEPTS_DIR}. Run generator first.")
        sys.exit(1)

    # Sample leaf applications
    leaf_apps = [f"pod_{p:02d}_app_{a:03d}" for p in range(1, 51) for a in range(1, 10)]
    sample_targets = random.sample(leaf_apps, min(100, len(leaf_apps)))

    logger.info(f"Executing 100 randomized upstream traversals across 50,000 CIs in memory...")

    latencies_us = []
    hop_counts = []
    sample_paths = []

    for target in sample_targets:
        path, dur_us = walk_upstream_root(target, max_depth=10)
        latencies_us.append(dur_us)
        hop_counts.append(len(path) - 1)
        if len(sample_paths) < 3:
            sample_paths.append({"target": target, "hops": len(path) - 1, "path": path, "latency_us": dur_us})

    p50_us = round(statistics.median(latencies_us), 2)
    p95_us = round(statistics.quantiles(latencies_us, n=20)[18], 2)
    p99_us = round(max(latencies_us), 2)
    avg_hops = round(statistics.mean(hop_counts), 1)

    receipt = {
        "engine": "StackLabs POSIX VFS 50K Topology Benchmark",
        "benchmark_date": time.strftime("%Y-%m-%d %H:%M:%S EDT"),
        "total_cis_in_graph": 50000,
        "sample_size": len(sample_targets),
        "average_hops_traversed": avg_hops,
        "latency_metrics_microseconds": {
            "min_us": round(min(latencies_us), 2),
            "p50_median_us": p50_us,
            "p95_us": p95_us,
            "p99_max_us": p99_us
        },
        "sample_traversals": sample_paths
    }

    print("\n" + "=" * 80)
    print(" 📊 50,000-NODE IN-MEMORY CMDB TRAVERSAL BENCHMARK RECEIPTS")
    print("=" * 80)
    print(f" Sample Count:       100 Leaf Applications")
    print(f" Average Graph Depth: {avg_hops} Hops")
    print(f" p50 Median Latency:  {p50_us} microseconds (0.{int(p50_us):03d} ms)")
    print(f" p95 Latency:         {p95_us} microseconds")
    print(f" p99 Maximum Latency: {p99_us} microseconds")
    print(f" Comparison to WAN:   ~{round(600000 / max(p50_us, 0.001)):,}x faster than 600ms Cloud WAN REST")
    print("=" * 80)

    RECEIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = RECEIPT_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    os.replace(temp_file, RECEIPT_FILE)

    print(f"[+] Atomically wrote benchmark telemetry receipt to {RECEIPT_FILE}")


if __name__ == "__main__":
    main()
