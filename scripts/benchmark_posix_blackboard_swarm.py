#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs POSIX Shared-Memory Blackboard Multi-Agent Swarm Benchmark
Path: /home/james/stacklabs/scripts/benchmark_posix_blackboard_swarm.py
Benchmarks atomic POSIX VFS blackboard task coordination against standard
serialized JSON payload coordination across 50 sequential agent pipeline tasks.

Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Governing Spec: WO0011088
"""

import os
import sys
import json
import time
import shutil
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("posix_blackboard_benchmark")

SHM_ROOT = Path("/dev/shm/blackboard")
RECEIPT_FILE = Path("/home/james/stacklabs/data/telemetry/posix_blackboard_benchmark_receipt.json")
TOTAL_TASKS = 50


def reset_shm_blackboard():
    if SHM_ROOT.exists():
        shutil.rmtree(SHM_ROOT)
    (SHM_ROOT / "agents" / "planner").mkdir(parents=True, exist_ok=True)
    (SHM_ROOT / "agents" / "worker_01").mkdir(parents=True, exist_ok=True)
    (SHM_ROOT / "agents" / "auditor_01").mkdir(parents=True, exist_ok=True)
    (SHM_ROOT / "tasks").mkdir(parents=True, exist_ok=True)
    (SHM_ROOT / "claims").mkdir(parents=True, exist_ok=True)
    (SHM_ROOT / "completed").mkdir(parents=True, exist_ok=True)


def run_json_baseline(task_count: int):
    logger.info(f"Executing Lane A: JSON Message-Passing Baseline ({task_count} tasks)...")
    t_start = time.perf_counter_ns()

    total_characters_transmitted = 0
    conversation_context = []

    for task_id in range(1, task_count + 1):
        task_slug = f"task_{task_id:04d}"

        # 1. Planner emits task payload with flat history slice (avoiding recursive dict explosion)
        flat_history_plan = [
            {"turn": m["turn"], "sender": m["sender"], "task_id": m["task_id"], "status": m.get("status", m.get("action"))}
            for m in conversation_context[-3:]
        ]
        plan_msg = {
            "turn": len(conversation_context) + 1,
            "sender": "planner",
            "task_id": task_slug,
            "action": "ASSIGN",
            "spec": f"Extract structural invariants for entity cluster {task_slug}",
            "context_history": flat_history_plan
        }
        serialized_plan = json.dumps(plan_msg)
        total_characters_transmitted += len(serialized_plan)
        conversation_context.append(plan_msg)

        # 2. Worker parses, simulates work, emits response
        incoming_plan = json.loads(serialized_plan)
        flat_history_worker = [
            {"turn": m["turn"], "sender": m["sender"], "task_id": m["task_id"], "status": m.get("status", m.get("action"))}
            for m in conversation_context[-3:]
        ]
        worker_msg = {
            "turn": len(conversation_context) + 1,
            "sender": "worker_01",
            "task_id": incoming_plan["task_id"],
            "status": "COMPLETED",
            "output": {"invariants_found": 3, "digest": f"0x{task_id:08x}"},
            "context_history": flat_history_worker
        }
        serialized_worker = json.dumps(worker_msg)
        total_characters_transmitted += len(serialized_worker)
        conversation_context.append(worker_msg)

        # 3. Auditor parses, verifies, emits audit report
        incoming_work = json.loads(serialized_worker)
        flat_history_audit = [
            {"turn": m["turn"], "sender": m["sender"], "task_id": m["task_id"], "status": m.get("status", m.get("action"))}
            for m in conversation_context[-3:]
        ]
        audit_msg = {
            "turn": len(conversation_context) + 1,
            "sender": "auditor_01",
            "task_id": incoming_work["task_id"],
            "status": "VERIFIED",
            "receipt": {"verified": True, "code": 0},
            "context_history": flat_history_audit
        }
        serialized_audit = json.dumps(audit_msg)
        total_characters_transmitted += len(serialized_audit)
        conversation_context.append(audit_msg)

    t_end = time.perf_counter_ns()
    duration_ms = (t_end - t_start) / 1_000_000.0

    # Approx 4 chars per token rule of thumb
    tokens_consumed = int(total_characters_transmitted / 4)

    return {
        "duration_ms": round(duration_ms, 2),
        "total_characters": total_characters_transmitted,
        "coordination_tokens_consumed": tokens_consumed,
        "latency_per_task_us": round(((t_end - t_start) / task_count) / 1000.0, 2)
    }


def run_posix_blackboard(task_count: int):
    logger.info(f"Executing Lane B: POSIX VFS Blackboard ({task_count} tasks)...")
    reset_shm_blackboard()

    t_start = time.perf_counter_ns()
    total_characters_transmitted = 0

    for task_id in range(1, task_count + 1):
        task_slug = f"task_{task_id:04d}"
        task_dir = SHM_ROOT / "tasks" / task_slug
        task_dir.mkdir(parents=True, exist_ok=True)

        # 1. Planner writes scalar spec
        spec_text = f"target={task_slug}\n"
        spec_file = task_dir / "spec.txt"
        spec_file.write_text(spec_text)
        total_characters_transmitted += len(spec_text)

        status_file = task_dir / "status.txt"
        status_file.write_text("READY\n")

        # 2. Worker claims task via atomic relative symlink
        claim_symlink = SHM_ROOT / "claims" / task_slug
        try:
            os.symlink("../agents/worker_01", claim_symlink)
        except FileExistsError:
            pass  # Atomic guarantee

        # Worker writes scalar completion
        output_file = task_dir / "output.txt"
        output_payload = f"invariants=3\ndigest=0x{task_id:08x}\n"
        output_file.write_text(output_payload)
        total_characters_transmitted += len(output_payload)
        status_file.write_text("COMPLETED\n")

        # 3. Auditor reads status, verifies, creates completion symlink
        current_status = status_file.read_text().strip()
        if current_status == "COMPLETED":
            completion_symlink = SHM_ROOT / "completed" / task_slug
            try:
                os.symlink(f"../tasks/{task_slug}", completion_symlink)
            except FileExistsError:
                pass
            status_file.write_text("VERIFIED\n")

    t_end = time.perf_counter_ns()
    duration_ms = (t_end - t_start) / 1_000_000.0
    tokens_consumed = int(total_characters_transmitted / 4)

    return {
        "duration_ms": round(duration_ms, 2),
        "total_characters": total_characters_transmitted,
        "coordination_tokens_consumed": tokens_consumed,
        "latency_per_task_us": round(((t_end - t_start) / task_count) / 1000.0, 2)
    }


def main():
    logger.info("Initializing StackLabs POSIX Blackboard Swarm Benchmark...")

    json_results = run_json_baseline(TOTAL_TASKS)
    posix_results = run_posix_blackboard(TOTAL_TASKS)

    speedup = round(json_results["latency_per_task_us"] / max(posix_results["latency_per_task_us"], 0.001), 2)
    token_cut_pct = round((1.0 - (posix_results["coordination_tokens_consumed"] / max(json_results["coordination_tokens_consumed"], 1))) * 100.0, 2)

    receipt = {
        "engine": "StackLabs POSIX Shared-Memory Blackboard Swarm Benchmark",
        "benchmark_date": time.strftime("%Y-%m-%d %H:%M:%S EDT"),
        "total_sequential_tasks": TOTAL_TASKS,
        "lane_a_json_message_passing": json_results,
        "lane_b_posix_shm_blackboard": posix_results,
        "performance_differential": {
            "coordination_speedup": f"{speedup}x faster",
            "token_reduction_percent": f"{token_cut_pct}% reduction",
            "posix_task_latency_us": posix_results["latency_per_task_us"],
            "json_task_latency_us": json_results["latency_per_task_us"]
        }
    }

    print("\n" + "=" * 80)
    print(" 📊 POSIX SHARED-MEMORY BLACKBOARD SWARM BENCHMARK RECEIPTS")
    print("=" * 80)
    print(f" Total Sequential Tasks:  {TOTAL_TASKS}")
    print(f" Lane A (JSON Passing):   {json_results['duration_ms']} ms | {json_results['coordination_tokens_consumed']:,} tokens | {json_results['latency_per_task_us']} µs/task")
    print(f" Lane B (POSIX VFS SHM):  {posix_results['duration_ms']} ms | {posix_results['coordination_tokens_consumed']:,} tokens | {posix_results['latency_per_task_us']} µs/task")
    print(f" Token Reduction:         {token_cut_pct}%")
    print(f" Coordination Speedup:    {speedup}x")
    print("=" * 80)

    RECEIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = RECEIPT_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    os.replace(temp_file, RECEIPT_FILE)

    print(f"[+] Atomically wrote benchmark receipt to {RECEIPT_FILE}")


if __name__ == "__main__":
    main()
