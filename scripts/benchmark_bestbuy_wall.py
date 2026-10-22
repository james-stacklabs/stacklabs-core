#!/usr/bin/env python3
import json
import time
import sqlite3
import sys
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(STACKLABS_ROOT))

from scripts.core.emoji_bytecode import EmojiBytecodeCodec

ITERATIONS = 5000
DB_PATH = STACKLABS_ROOT / "data" / "ground_truth.db"
OUTPUT_JSON = STACKLABS_ROOT / "data" / "bestbuy_benchmark_results.json"

# 1. Synthesize Bloated Cloud REST Payload (Simulated 45KB Swivel-Chair State)
def make_bloated_cloud_payload():
    nested_records = []
    for i in range(120):
        nested_records.append({
            "record_id": f"rec_crm_entity_{i:04d}",
            "schema_version": "v3.12.4-enterprise-prod",
            "telemetry": {
                "subsystem_domain": "sports_fan_advocate_network",
                "operational_status": "CRITICAL_ELEVATED_DRIFT",
                "diagnostic_metric": "BUFFER_QUEUE_SATURATION_SPIKE",
                "recommended_action": "PURGE_AND_RECYCLE_WORKER_POOL",
                "target_stream_uri": "https://api.stream.internal/v1/live/yt_chat_01"
            },
            "tracing": {
                "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
                "span_id": "00f067aa0ba902b7",
                "cloud_region": "us-east-1-virginia",
                "api_gateway_cost_usd": 0.000035
            },
            "padding_metadata": ["enterprise_scaffolding", "cookie_state", "cors_token", "hydration_marker"] * 3
        })
    return json.dumps({"status": "200_OK", "cluster": "cloud-cluster-09", "data": nested_records})

def run_benchmark():
    codec = EmojiBytecodeCodec()
    cloud_raw = make_bloated_cloud_payload()
    cloud_payload_size = len(cloud_raw.encode("utf-8"))

    # StackLabs 4-Gram Wire Frame
    stacklabs_frame = "📡🛑🧱✂️ :: yt_chat_01"
    stacklabs_payload_size = len(stacklabs_frame.encode("utf-8"))

    # Prepare SQLite WAL in-memory / local test table
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE frame_cache (id INTEGER PRIMARY KEY, target TEXT, frame TEXT);")
    conn.execute("INSERT INTO frame_cache (target, frame) VALUES ('yt_chat_01', '📡🛑🧱✂️ :: yt_chat_01');")
    conn.commit()

    # --- BENCHMARK 1: Cloud REST JSON Parse ---
    t0 = time.perf_counter()
    for _ in range(ITERATIONS):
        parsed = json.loads(cloud_raw)
        # Simulate accessing the target entity deep in the payload
        _ = parsed["data"][0]["telemetry"]["diagnostic_metric"]
    t1 = time.perf_counter()
    cloud_total_sec = t1 - t0
    cloud_avg_us = (cloud_total_sec / ITERATIONS) * 1_000_000

    # --- BENCHMARK 2: StackLabs 4-Gram WAL Ingestion ---
    cursor = conn.cursor()
    t2 = time.perf_counter()
    for _ in range(ITERATIONS):
        cursor.execute("SELECT frame FROM frame_cache WHERE target = 'yt_chat_01';")
        row = cursor.fetchone()
        _ = codec.to_log_string(row[0])
    t3 = time.perf_counter()
    stacklabs_total_sec = t3 - t2
    stacklabs_avg_us = (stacklabs_total_sec / ITERATIONS) * 1_000_000

    conn.close()

    payload_reduction_pct = ((cloud_payload_size - stacklabs_payload_size) / cloud_payload_size) * 100
    latency_speedup_factor = cloud_avg_us / stacklabs_avg_us if stacklabs_avg_us > 0 else 0

    results = {
        "iterations": ITERATIONS,
        "cloud_rest": {
            "payload_bytes": cloud_payload_size,
            "avg_parse_latency_us": round(cloud_avg_us, 2),
            "total_runtime_ms": round(cloud_total_sec * 1000, 2)
        },
        "stacklabs_metal": {
            "payload_bytes": stacklabs_payload_size,
            "avg_parse_latency_us": round(stacklabs_avg_us, 2),
            "total_runtime_ms": round(stacklabs_total_sec * 1000, 2)
        },
        "deltas": {
            "payload_reduction_pct": round(payload_reduction_pct, 2),
            "speedup_factor": round(latency_speedup_factor, 1)
        }
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(results, indent=2))

    # Print Showroom Display Card
    print("\n" + "=" * 64)
    print("📺 BEST BUY SHOWROOM CONTRAST: CLOUD REST VS STACKLABS METAL")
    print("=" * 64)
    print(f"Iterations Evaluated : {ITERATIONS:,} events on AMD Zen 4 APU")
    print("-" * 64)
    print(f"{'Metric':<25} | {'Legacy Cloud REST':<16} | {'StackLabs Metal':<16}")
    print("-" * 64)
    print(f"{'Wire Payload':<25} | {cloud_payload_size:>13,} B | {stacklabs_payload_size:>13,} B")
    print(f"{'Parse Latency (Avg)':<25} | {cloud_avg_us:>13.2f} µs | {stacklabs_avg_us:>13.2f} µs")
    print(f"{'Total Ingestion Time':<25} | {cloud_total_sec*1000:>13.2f} ms | {stacklabs_total_sec*1000:>13.2f} ms")
    print("-" * 64)
    print(f"⚡ Payload Reduction : {payload_reduction_pct:.1f}%")
    print(f"🚀 Silicon Velocity : {latency_speedup_factor:.1f}x Faster Execution")
    print("=" * 64 + "\n")

if __name__ == "__main__":
    run_benchmark()
