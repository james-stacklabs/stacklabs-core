#!/home/james/stacklabs/.venv/bin/python3
"""
scripts/benchmark_vfs_wiki_dual_plane.py
=========================================
Dual-Plane Knowledge Fabric & Swanson Collider Performance Benchmark.
Governed by Invariant 15 (Two-Call Mandate) and Invariant 36 (System Verification).

Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
"""

import os
import sys
import json
import time
import urllib.request
from pathlib import Path

VFS_DB_PATH = Path("/home/james/stacklabs/vfs/vfs_wiki.db")
RECEIPT_FILE = Path("/home/james/stacklabs/data/telemetry/vfs_wiki_dual_plane_benchmark.json")

def get_synapse_port() -> int:
    env_file = Path("/home/james/stacklabs/.env")
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            if line.startswith("SYNAPSE_PORT="):
                val = line.split("=", 1)[1].strip()
                if val.isdigit():
                    return int(val)
    return 8088

def run_benchmarks():
    print("====================================================================")
    print("🏛️ STACKLABS PLATFORM: DUAL-PLANE KNOWLEDGE FABRIC BENCHMARK")
    print("====================================================================")
    
    receipt = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": "clio",
        "tests": {}
    }

    # ----------------------------------------------------------------------
    # BENCHMARK 1: Storage Plane & Memory Footprint Audit
    # ----------------------------------------------------------------------
    print("\n[BENCHMARK 1] Auditing SQLite WAL Storage Plane & RAM Footprint...")
    if not VFS_DB_PATH.is_file():
        print(f"  ⚠ Warning: Master DB not found at {VFS_DB_PATH}. Running in filesystem mode.")
        db_size_mb = 0.0
    else:
        db_size_mb = VFS_DB_PATH.stat().st_size / (1024 * 1024)
        print(f"  ✔ SQLite WAL Master Database: {VFS_DB_PATH} ({db_size_mb:.2f} MB)")

    receipt["tests"]["storage_audit"] = {
        "db_path": str(VFS_DB_PATH),
        "db_size_mb": round(db_size_mb, 2),
        "status": "PASS"
    }

    # ----------------------------------------------------------------------
    # BENCHMARK 2: Live Synapse Blueprint API Probe (Call 1)
    # ----------------------------------------------------------------------
    port = get_synapse_port()
    base_url = f"http://127.0.0.1:{port}"
    print(f"\n[BENCHMARK 2] Live Synapse Blueprint Verification on Port {port}...")

    # Test /api/wiki/stats
    stats_url = f"{base_url}/api/wiki/stats"
    try:
        with urllib.request.urlopen(stats_url, timeout=5) as resp:
            stats_code = resp.getcode()
            stats_data = json.loads(resp.read().decode())
            print(f"  ✔ GET {stats_url} -> HTTP {stats_code}")
            print(f"      Storage Mode:   {stats_data.get('storage_mode')}")
            print(f"      Total Concepts: {stats_data.get('total_concepts', 0):,}")
    except Exception as e:
        print(f"  ❌ Error probing stats: {e}")
        stats_code = 500
        stats_data = {}

    # Test /api/wiki/concepts
    search_url = f"{base_url}/api/wiki/concepts?q=mets&limit=5"
    try:
        with urllib.request.urlopen(search_url, timeout=5) as resp:
            search_code = resp.getcode()
            search_data = json.loads(resp.read().decode())
            print(f"  ✔ GET {search_url} -> HTTP {search_code} ({len(search_data.get('concepts', []))} matches)")
    except Exception as e:
        print(f"  ❌ Error probing search: {e}")
        search_code = 500
        search_data = {}

    receipt["tests"]["api_probe"] = {
        "port": port,
        "stats_code": stats_code,
        "search_code": search_code,
        "storage_mode": stats_data.get("storage_mode", "unknown"),
        "total_concepts": stats_data.get("total_concepts", 0),
        "status": "PASS" if stats_code == 200 and search_code == 200 else "FAIL"
    }

    # ----------------------------------------------------------------------
    # BENCHMARK 3: Bidirectional BFS & Super-Hub Suppression (Call 2)
    # ----------------------------------------------------------------------
    print("\n[BENCHMARK 3] Measuring Swanson Crawl Latency & Hub Suppression...")
    crawl_url = f"{base_url}/api/wiki/swanson_crawl"
    crawl_payload = json.dumps({
        "source": "metsapere",
        "target": "metsalauka",
        "mode": "path",
        "dampen_super_hubs": True,
        "max_hub_degree": 5000
    }).encode("utf-8")

    req = urllib.request.Request(crawl_url, data=crawl_payload, headers={"Content-Type": "application/json"})
    try:
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=10) as resp:
            crawl_code = resp.getcode()
            crawl_data = json.loads(resp.read().decode())
        t1 = time.perf_counter()
        measured_ms = (t1 - t0) * 1000.0

        print(f"  ✔ POST {crawl_url} -> HTTP {crawl_code}")
        print(f"      Path:        {' -> '.join(crawl_data.get('path', []))}")
        print(f"      API Latency: {crawl_data.get('latency_ms')} ms")
        print(f"      Client RTT:  {measured_ms:.2f} ms")
        print(f"      Hubs Damped: {crawl_data.get('super_hubs_dampened')}")
    except Exception as e:
        print(f"  ❌ Error executing crawl: {e}")
        crawl_code = 500
        crawl_data = {}
        measured_ms = 0.0

    receipt["tests"]["swanson_crawl"] = {
        "crawl_code": crawl_code,
        "latency_ms": crawl_data.get("latency_ms", measured_ms),
        "hops": crawl_data.get("hops", -1),
        "path": crawl_data.get("path", []),
        "status": "PASS" if crawl_code == 200 else "FAIL"
    }

    # Write receipt
    RECEIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_FILE.write_text(json.dumps(receipt, indent=2))
    print(f"\n✔ Empirical receipt written to {RECEIPT_FILE}")
    print("====================================================================")


def main():
    run_benchmarks()


if __name__ == "__main__":
    main()
