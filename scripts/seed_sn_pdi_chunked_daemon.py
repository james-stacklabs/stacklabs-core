#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Autonomous Chunked ServiceNow PDI Topology Ingestion Daemon
Path: /home/james/stacklabs/scripts/seed_sn_pdi_chunked_daemon.py
Pushes synthetic enterprise topology pod-by-pod into ServiceNow dev186522
using deterministic 32-hex sys_ids, rate-limited chunks, and stateful checkpointing.

Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Governing Spec: WO0011087
"""

import os
import sys
import time
import json
import sqlite3
import hashlib
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sn_pdi_seeder")

DB_PATH = Path("/home/james/stacklabs/vfs/cmdb_synthetic_50k.db")
PROGRESS_FILE = Path("/home/james/stacklabs/data/telemetry/sn_pdi_seed_progress.json")

# ServiceNow PDI Credentials
SN_INSTANCE = os.getenv("SN_INSTANCE", "https://dev186522.service-now.com")
SN_USER = os.getenv("SN_USER", "admin")
SN_PASS = os.getenv("SN_PASS", "J-Slf7SPmg!2")
AUTH = (SN_USER, SN_PASS)

# Canonical Relationship Types in dev186522
REL_TYPE_MAP = {
    "connects_to": "5599a965c0a8010e00da3b58b113d70e",    # Connects to::Connected by
    "hosts": "5f985e0ec0a8010e00a9714f2a172815",          # Hosted on::Hosts
    "depends_on": "1a9cb166f1571100a92eb60da2bce5c5",     # Depends on::Used by
    "uplink": "5599a965c0a8010e00da3b58b113d70e",         # Connects to::Connected by
    "calls": "1a9cb166f1571100a92eb60da2bce5c5",          # Depends on::Used by
    "replicates_to": "607b15e1c0a8010e00a4413059767eec",   # Receives data from::Sends data to
    "fails_over_to": "63032f62c0a8010e0081e1f99c876bf7",   # DR provided by::Provides DR for
    "backed_up_by": "63032f62c0a8010e0081e1f99c876bf7"    # DR provided by::Provides DR for
}

def to_sys_id(name: str) -> str:
    """Generate deterministic 32-character hexadecimal sys_id."""
    return hashlib.md5(f"stacklabs_{name}".encode("utf-8")).hexdigest()

def load_checkpoint() -> Dict[str, Any]:
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading checkpoint, reinitializing: {e}")
    return {
        "status": "INITIALIZED",
        "completed_pods": [],
        "total_cis_pushed": 0,
        "total_rels_pushed": 0,
        "last_pod": 0,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S EDT")
    }

def save_checkpoint(state: Dict[str, Any]):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S EDT")
    temp_file = PROGRESS_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(temp_file, PROGRESS_FILE)

def push_ci_record(session: requests.Session, table: str, payload: dict, max_retries: int = 3) -> bool:
    url = f"{SN_INSTANCE}/api/now/table/{table}"
    for attempt in range(max_retries):
        try:
            res = session.post(url, json=payload, timeout=12)
            if res.status_code in (200, 201):
                return True
            elif res.status_code == 409 or "already exists" in res.text or "duplicate" in res.text.lower():
                return True  # Idempotent skip
            elif res.status_code in (400, 403) and "Error during insert" in res.text:
                # Idempotency check: record already exists
                chk = session.get(f"{url}/{payload['sys_id']}?sysparm_fields=sys_id", timeout=6)
                if chk.status_code == 200:
                    return True
                return False
            elif res.status_code in (429, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            else:
                logger.warning(f"Failed to insert {payload.get('name')} into {table}: HTTP {res.status_code}")
                return False
        except requests.RequestException:
            time.sleep(1.5 * (attempt + 1))
    return False

def push_rel_record(session: requests.Session, parent_id: str, child_id: str, type_id: str, max_retries: int = 3) -> bool:
    url = f"{SN_INSTANCE}/api/now/table/cmdb_rel_ci"
    rel_id = hashlib.md5(f"stacklabs_rel_{parent_id}_{child_id}_{type_id}".encode("utf-8")).hexdigest()
    payload = {
        "sys_id": rel_id,
        "parent": parent_id,
        "child": child_id,
        "type": type_id
    }
    for attempt in range(max_retries):
        try:
            res = session.post(url, json=payload, timeout=12)
            if res.status_code in (200, 201):
                return True
            elif res.status_code == 409 or "already exists" in res.text or "duplicate" in res.text.lower():
                return True
            elif res.status_code in (400, 403) and "Error during insert" in res.text:
                chk = session.get(f"{url}/{rel_id}?sysparm_fields=sys_id", timeout=6)
                if chk.status_code == 200:
                    return True
                return False
            elif res.status_code in (429, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            else:
                return False
        except requests.RequestException:
            time.sleep(1.5 * (attempt + 1))
    return False

def seed_pod(conn: sqlite3.Connection, session: requests.Session, pod_num: int, state: Dict[str, Any], rate_limit_sleep: float = 0.05, workers: int = 3) -> bool:
    pod_str = f"pod_{pod_num:02d}"
    logger.info(f"--- [STARTING POD {pod_num:02d}] Fetching CIs & relationships from SQLite ---")

    # Fetch CIs for this pod
    cursor = conn.cursor()
    cursor.execute("SELECT sys_id, name, sys_class_name, tier, status FROM cmdb_ci WHERE name LIKE ?", (f"{pod_str}_%",))
    cis = cursor.fetchall()

    logger.info(f"Pod {pod_num:02d}: Ingesting {len(cis)} CIs to ServiceNow (workers={workers}, delay={rate_limit_sleep}s)...")
    ci_success = 0
    t0_ci = time.time()

    def process_ci(row):
        sys_id_raw, name, class_name, tier, status = row
        sn_id = to_sys_id(name)
        payload = {
            "sys_id": sn_id,
            "name": name,
            "operational_status": "1" if status == "OPERATIONAL" else "2",
            "short_description": f"StackLabs Synthetic Tier {tier} Infrastructure ({pod_str})"
        }
        ok = push_ci_record(session, class_name, payload)
        if rate_limit_sleep > 0:
            time.sleep(rate_limit_sleep)
        return ok

    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for idx, ok in enumerate(executor.map(process_ci, cis)):
                if ok:
                    ci_success += 1
                if (idx + 1) % 200 == 0:
                    logger.info(f"Pod {pod_num:02d}: Ingested {idx + 1}/{len(cis)} CIs ({(idx + 1)/len(cis)*100:.1f}%)...")
    else:
        for idx, row in enumerate(cis):
            if process_ci(row):
                ci_success += 1
            if (idx + 1) % 200 == 0:
                logger.info(f"Pod {pod_num:02d}: Ingested {idx + 1}/{len(cis)} CIs ({(idx + 1)/len(cis)*100:.1f}%)...")

    elapsed_ci = time.time() - t0_ci
    logger.info(f"Pod {pod_num:02d}: Ingested {ci_success}/{len(cis)} CIs in {elapsed_ci:.2f}s ({ci_success/max(elapsed_ci, 0.001):.1f} req/s).")

    state["total_cis_pushed"] += ci_success
    save_checkpoint(state)

    # Fetch relationships for this pod
    cursor.execute("""
        SELECT parent, child, type FROM cmdb_rel_ci 
        WHERE parent LIKE ? OR child LIKE ?
    """, (f"{pod_str}_%", f"{pod_str}_%"))
    rels = cursor.fetchall()

    logger.info(f"Pod {pod_num:02d}: Ingesting {len(rels)} relationships to cmdb_rel_ci (workers={workers}, delay={rate_limit_sleep}s)...")
    rel_success = 0
    t0_rel = time.time()

    def process_rel(row):
        parent_name, child_name, rel_type = row
        parent_sn_id = to_sys_id(parent_name)
        child_sn_id = to_sys_id(child_name)
        type_sn_id = REL_TYPE_MAP.get(rel_type, REL_TYPE_MAP["depends_on"])
        ok = push_rel_record(session, parent_sn_id, child_sn_id, type_sn_id)
        if rate_limit_sleep > 0:
            time.sleep(rate_limit_sleep)
        return ok

    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for idx, ok in enumerate(executor.map(process_rel, rels)):
                if ok:
                    rel_success += 1
                if (idx + 1) % 500 == 0:
                    logger.info(f"Pod {pod_num:02d}: Ingested {idx + 1}/{len(rels)} relationships ({(idx + 1)/len(rels)*100:.1f}%)...")
    else:
        for idx, row in enumerate(rels):
            if process_rel(row):
                rel_success += 1
            if (idx + 1) % 500 == 0:
                logger.info(f"Pod {pod_num:02d}: Ingested {idx + 1}/{len(rels)} relationships ({(idx + 1)/len(rels)*100:.1f}%)...")

    elapsed_rel = time.time() - t0_rel
    logger.info(f"Pod {pod_num:02d}: Ingested {rel_success}/{len(rels)} relationships in {elapsed_rel:.2f}s ({rel_success/max(elapsed_rel, 0.001):.1f} req/s).")

    state["total_rels_pushed"] += rel_success
    if pod_num not in state["completed_pods"]:
        state["completed_pods"].append(pod_num)
    state["last_pod"] = pod_num
    save_checkpoint(state)
    logger.info(f"Pod {pod_num:02d}: Complete. Total CIs in state: {state['total_cis_pushed']}, Total Rels: {state['total_rels_pushed']}.")
    return True

def main():
    parser = argparse.ArgumentParser(description="StackLabs Chunked ServiceNow PDI Topology Seeder")
    parser.add_argument("--single-pod", type=int, default=None, help="Seed only a single specific pod (e.g. 1)")
    parser.add_argument("--max-pods", type=int, default=50, help="Maximum number of pods to process")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between HTTP calls in seconds (default 0.05)")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent HTTP worker threads (default 3)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        logger.error(f"SQLite database missing at {DB_PATH}. Run generate_synthetic_cmdb_50k.py first.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    state = load_checkpoint()

    session = requests.Session()
    session.auth = AUTH
    session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    print("=" * 80)
    print(" 🚀 STACKLABS SERVICENOW PDI TOPOLOGY INGESTION DAEMON")
    print(f" Target Instance:    {SN_INSTANCE}")
    print(f" Source SQLite DB:   {DB_PATH}")
    print(f" Rate Pacing:        ~{args.workers / (0.11 + args.delay):.1f} req/s ({args.workers} workers, {args.delay}s delay)")
    print(f" Current Progress:   {len(state['completed_pods'])} pods completed")
    print("=" * 80)

    if args.single_pod:
        state["status"] = f"SEEDING_POD_{args.single_pod}"
        seed_pod(conn, session, args.single_pod, state, rate_limit_sleep=args.delay, workers=args.workers)
        state["status"] = f"POD_{args.single_pod}_COMPLETE"
        save_checkpoint(state)
        print(f"\n[+] Successfully finished single pod {args.single_pod} ingestion.")
        conn.close()
        return

    pods_to_run = [p for p in range(1, args.max_pods + 1) if p not in state["completed_pods"]]
    logger.info(f"Queued pods remaining: {len(pods_to_run)}")

    state["status"] = "STREAMING_BACKGROUND"
    save_checkpoint(state)

    for p in pods_to_run:
        seed_pod(conn, session, p, state, rate_limit_sleep=args.delay, workers=args.workers)
        logger.info(f"Progress checkpoint saved: Pod {p} complete. Sleeping 3s between pods...")
        time.sleep(3.0)

    state["status"] = "ALL_PODS_COMPLETE"
    save_checkpoint(state)
    conn.close()
    print("\n✅ All target pods synchronized to ServiceNow PDI.")

if __name__ == "__main__":
    main()
