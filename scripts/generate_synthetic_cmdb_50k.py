#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs 50,000-Node Synthetic CMDB Generator
Path: /home/james/stacklabs/scripts/generate_synthetic_cmdb_50k.py
Generates a dense, multi-tier enterprise topology into SQLite WAL and
projects the graph directly into Linux shared memory (/dev/shm/vfs/cmdb_50k/).

Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Governing Spec: WO0011086
"""

import os
import sys
import time
import shutil
import sqlite3
import logging
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cmdb_50k_generator")

DB_PATH = Path("/home/james/stacklabs/vfs/cmdb_synthetic_50k.db")
SHM_ROOT = Path("/dev/shm/vfs/cmdb_50k")
CONCEPTS_DIR = SHM_ROOT / "ci"


def setup_database(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("""
        CREATE TABLE cmdb_ci (
            sys_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sys_class_name TEXT NOT NULL,
            tier INTEGER NOT NULL,
            status TEXT NOT NULL
        );
    """)
    conn.execute("""
        CREATE TABLE cmdb_rel_ci (
            parent TEXT NOT NULL,
            child TEXT NOT NULL,
            type TEXT NOT NULL,
            PRIMARY KEY (parent, child, type)
        );
    """)
    return conn


def reset_shm_plane():
    if SHM_ROOT.exists():
        shutil.rmtree(SHM_ROOT)
    CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_topology() -> Tuple[List[Tuple[str, str, str, int, str]], List[Tuple[str, str, str]]]:
    cis = []
    rels = []

    # 50 Pods across 5 Tiers
    # Tier 1: 500 Core & Spine Switches (10 per Pod)
    # Tier 2: 2,500 Hypervisors (50 per Pod)
    # Tier 3: 25,000 Compute VMs (500 per Pod, 10 per Hypervisor)
    # Tier 4: 7,000 Database Clusters (140 per Pod)
    # Tier 5: 15,000 Application Services (300 per Pod)
    # Total CIs: 500 + 2,500 + 25,000 + 7,000 + 15,000 = 50,000
    # Dense multi-tier relationships: >150,000 relationships across pods

    logger.info("Synthesizing 50,000 enterprise CIs across 50 data center pods...")

    for pod in range(1, 51):
        pod_str = f"pod_{pod:02d}"

        # Tier 1: Switches (10 switches: sw_01, sw_02 are spine switches, sw_03..sw_10 are leaf switches)
        switches = [f"{pod_str}_sw_{s:02d}" for s in range(1, 11)]
        for sw in switches:
            cis.append((sw, sw, "cmdb_ci_ip_switch", 1, "OPERATIONAL"))

        # Leaf-to-spine uplinks (sw_03 through sw_10 uplink to spine sw_01 and sw_02)
        for s_idx in range(2, 10):
            rels.append((switches[0], switches[s_idx], "uplink"))
            rels.append((switches[1], switches[s_idx], "uplink"))

        # Tier 2: Hypervisors (50 hypervisors, dual-homed to switches)
        hypervisors = [f"{pod_str}_hyp_{h:02d}" for h in range(1, 51)]
        for idx, hyp in enumerate(hypervisors):
            cis.append((hyp, hyp, "cmdb_ci_esx_server", 2, "OPERATIONAL"))
            parent_sw1 = switches[idx % len(switches)]
            parent_sw2 = switches[(idx + 1) % len(switches)]
            rels.append((parent_sw1, hyp, "connects_to"))
            rels.append((parent_sw2, hyp, "connects_to"))

        # Tier 3: VMs (500 VMs per pod)
        vms = [f"{pod_str}_vm_{v:03d}" for v in range(1, 501)]
        for idx, vm in enumerate(vms):
            cis.append((vm, vm, "cmdb_ci_vm_instance", 3, "OPERATIONAL"))
            parent_hyp = hypervisors[idx % len(hypervisors)]
            alt_hyp = hypervisors[(idx + 1) % len(hypervisors)]
            rels.append((parent_hyp, vm, "hosts"))
            rels.append((alt_hyp, vm, "fails_over_to"))

        # Tier 4: Databases (140 DBs per pod)
        dbs = [f"{pod_str}_db_{d:03d}" for d in range(1, 141)]
        for idx, db in enumerate(dbs):
            cis.append((db, db, "cmdb_ci_database", 4, "OPERATIONAL"))
            host_vm = vms[idx % len(vms)]
            backup_vm = vms[(idx + 140) % len(vms)]
            target_replica = dbs[(idx + 1) % len(dbs)]
            rels.append((host_vm, db, "hosts"))
            rels.append((backup_vm, db, "backed_up_by"))
            rels.append((db, target_replica, "replicates_to"))

        # Tier 5: Application Services (300 Apps per pod)
        apps = [f"{pod_str}_app_{a:03d}" for a in range(1, 301)]
        for idx, app in enumerate(apps):
            cis.append((app, app, "cmdb_ci_appl", 5, "OPERATIONAL"))
            # Primary and read-replica database dependencies
            target_db1 = dbs[idx % len(dbs)]
            target_db2 = dbs[(idx + 1) % len(dbs)]
            rels.append((app, target_db1, "depends_on"))
            rels.append((app, target_db2, "depends_on"))

            # VM cluster hosts (load-balanced across 2 compute VMs)
            app_host_vm1 = vms[(idx * 3) % len(vms)]
            app_host_vm2 = vms[(idx * 3 + 1) % len(vms)]
            rels.append((app_host_vm1, app, "hosts"))
            rels.append((app_host_vm2, app, "hosts"))

            # Service-to-service downstream microservice dependency
            downstream_app = apps[(idx + 1) % len(apps)]
            rels.append((app, downstream_app, "calls"))

    return cis, rels


def project_to_vfs(cis: List[Tuple[str, str, str, int, str]], rels: List[Tuple[str, str, str]]):
    logger.info(f"Pre-creating {len(cis):,} CI directories in {CONCEPTS_DIR}...")
    for ci in cis:
        (CONCEPTS_DIR / ci[0]).mkdir(parents=True, exist_ok=True)

    logger.info(f"Projecting {len(rels):,} relationships into {CONCEPTS_DIR} as POSIX inodes and symlinks...")
    for parent, child, rel_type in rels:
        p_dir = CONCEPTS_DIR / parent
        c_dir = CONCEPTS_DIR / child

        # Forward link: parent/fwd_{rel_type}_{child} -> ../child
        fwd_edge = p_dir / f"fwd_{rel_type}_{child}"
        try:
            os.symlink(f"../{child}", fwd_edge)
        except OSError:
            pass

        # Reverse link: child/rev_{rel_type}_{parent} -> ../parent
        rev_edge = c_dir / f"rev_{rel_type}_{parent}"
        try:
            os.symlink(f"../{parent}", rev_edge)
        except OSError:
            pass


def main():
    t_start = time.perf_counter()
    reset_shm_plane()
    conn = setup_database(DB_PATH)

    cis, rels = generate_topology()

    logger.info(f"Writing {len(cis):,} CIs to SQLite WAL...")
    conn.executemany("INSERT INTO cmdb_ci VALUES (?, ?, ?, ?, ?)", cis)
    logger.info(f"Writing {len(rels):,} relationships to SQLite WAL...")
    conn.executemany("INSERT INTO cmdb_rel_ci VALUES (?, ?, ?)", rels)
    conn.commit()
    conn.close()

    project_to_vfs(cis, rels)

    elapsed = time.perf_counter() - t_start
    print("=" * 80)
    print(f" [PASS] 50,000-Node Synthetic CMDB Generated in {elapsed:.2f}s")
    print(f" SQLite Ledger: {DB_PATH}")
    print(f" In-Memory VFS: {CONCEPTS_DIR}")
    print(f" Total CIs: {len(cis):,} | Total Relationships: {len(rels):,}")
    print("=" * 80)


if __name__ == "__main__":
    main()
