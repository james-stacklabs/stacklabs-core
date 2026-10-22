#!/usr/bin/env python3
"""
Sovereign OS: Seed POSIX VFS 6-Module ITSM Proving Grounds
Path: /home/james/stacklabs/scripts/seed_vfs_itsm_proving_grounds.py
Author: James Carroll (Pilot) & Lead Systems Architect
"""
import os
import shutil
import stat
import json
import time
from pathlib import Path

VFS_ROOT = Path("/dev/shm/vfs")

def scaffold_structure():
    """Initializes clean directory tree and POSIX permission boundaries."""
    if VFS_ROOT.exists():
        shutil.rmtree(VFS_ROOT)
    
    modules = ["cmdb", "catalog", "tickets", "changes", "services", "hardware", "queues", "users"]
    for mod in modules:
        (VFS_ROOT / mod).mkdir(parents=True, exist_ok=True)
        
    # Permission boundaries
    os.chmod(VFS_ROOT / "changes", 0o770)

def seed_enterprise_footprint():
    """Seeds 5,000 CIs across servers, network, and storage."""
    print("[1/5] Seeding 5,000 enterprise CIs into /dev/shm/vfs/cmdb/...")
    start = time.perf_counter()
    
    # 1. 4,000 Servers
    servers_dir = VFS_ROOT / "cmdb" / "servers"
    servers_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 4001):
        s_dir = servers_dir / f"srv-{i:04d}"
        op_dir = s_dir / "operational"
        op_dir.mkdir(parents=True, exist_ok=True)
        (op_dir / "ip.txt").write_text(f"10.240.{(i // 254) % 254 + 1}.{i % 254 + 1}\n")
        (op_dir / "os.txt").write_text("Ubuntu 24.04 LTS x86_64\n")
        (op_dir / "status.txt").write_text("ONLINE\n")
        (op_dir / "env.txt").write_text("PROD\n" if i <= 3000 else "STAGING\n")
        
    # Seed canonical database anchor sea-db-01
    sea_db = servers_dir / "sea-db-01" / "operational"
    sea_db.mkdir(parents=True, exist_ok=True)
    (sea_db / "ip.txt").write_text("10.240.50.101\n")
    (sea_db / "os.txt").write_text("RHEL 9.4 Enterprise\n")
    (sea_db / "status.txt").write_text("ONLINE\n")
    (sea_db / "env.txt").write_text("PROD\n")
    (sea_db / "role.txt").write_text("PRIMARY_PAYROLL_DATABASE\n")

    # 2. 500 Network Switches
    net_dir = VFS_ROOT / "cmdb" / "network"
    net_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 501):
        sw_dir = net_dir / f"sw-{i:04d}" / "operational"
        sw_dir.mkdir(parents=True, exist_ok=True)
        (sw_dir / "ip.txt").write_text(f"10.250.1.{i}\n")
        (sw_dir / "status.txt").write_text("ACTIVE\n")

    # 3. 500 Storage Volumes
    san_dir = VFS_ROOT / "cmdb" / "storage"
    san_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 501):
        vol_dir = san_dir / f"san-{i:04d}" / "operational"
        vol_dir.mkdir(parents=True, exist_ok=True)
        (vol_dir / "capacity_gb.txt").write_text("10240\n")
        (vol_dir / "status.txt").write_text("ATTACHED\n")

    elapsed = time.perf_counter() - start
    print(f"      Seeded 5,000 CIs in {elapsed:.3f} seconds.")

def seed_bsm_tree():
    """Builds Business Service Map for sap_payroll with relative symlinks."""
    print("[2/5] Building BSM dependency tree for sap_payroll...")
    bsm_dir = VFS_ROOT / "services" / "sap_payroll"
    bsm_dir.mkdir(parents=True, exist_ok=True)
    
    (bsm_dir / "manifest.json").write_text(json.dumps({
        "service": "sap_payroll",
        "tier": "MISSION_CRITICAL",
        "business_owner": "Corporate Treasury",
        "sla_target": "99.99%"
    }, indent=2) + "\n")
    
    # Symlinks to operational infrastructure
    (bsm_dir / "lb").symlink_to("../../cmdb/network/sw-0001")
    
    web_pool = bsm_dir / "web_pool"
    web_pool.mkdir(parents=True, exist_ok=True)
    (web_pool / "web-01").symlink_to("../../../cmdb/servers/srv-0001")
    (web_pool / "web-02").symlink_to("../../../cmdb/servers/srv-0002")
    
    db_cluster = bsm_dir / "db_cluster"
    db_cluster.mkdir(parents=True, exist_ok=True)
    (db_cluster / "primary").symlink_to("../../../cmdb/servers/sea-db-01")

def seed_service_catalog():
    """Provisions Service Catalog Item provision_k8s_namespace."""
    print("[3/5] Provisioning Service Catalog Item provision_k8s_namespace...")
    item_dir = VFS_ROOT / "catalog" / "provision_k8s_namespace"
    item_dir.mkdir(parents=True, exist_ok=True)
    
    (item_dir / "manifest.json").write_text(json.dumps({
        "name": "provision_k8s_namespace",
        "title": "Provision Kubernetes Team Namespace",
        "category": "Cloud Infrastructure",
        "approval_required": False
    }, indent=2) + "\n")
    
    validate_sh = item_dir / "validate.sh"
    validate_sh.write_text("""#!/bin/bash
NS="$1"
if [[ -z "$NS" ]]; then
  echo "ERROR: Namespace name required" >&2
  exit 1
fi
if [[ ! "$NS" =~ ^[a-z0-9-]+$ ]]; then
  echo "ERROR: RFC 1123 DNS subdomain format violation" >&2
  exit 1
fi
echo "VALIDATED: $NS"
exit 0
""")
    validate_sh.chmod(0o750)
    
    fulfill_sh = item_dir / "fulfill.sh"
    fulfill_sh.write_text("""#!/bin/bash
NS="$1"
TARGET="/dev/shm/vfs/k8s/$NS"
mkdir -p "$TARGET"
echo "ACTIVE" > "$TARGET/status.txt"
echo "$(date -Iseconds)" > "$TARGET/created_at.txt"
echo "FULFILLED: $NS"
exit 0
""")
    fulfill_sh.chmod(0o750)

def seed_hardware_asset():
    """Provisions Hardware Asset blade-42 with HAM/SAM split."""
    print("[4/5] Provisioning Hardware Asset blade-42...")
    blade_dir = VFS_ROOT / "hardware" / "blade-42"
    fin_dir = blade_dir / "financial"
    op_dir = blade_dir / "operational"
    fin_dir.mkdir(parents=True, exist_ok=True)
    op_dir.mkdir(parents=True, exist_ok=True)
    
    (fin_dir / "po_number.txt").write_text("PO-8849201\n")
    (fin_dir / "cost.txt").write_text("14500.00 USD\n")
    (fin_dir / "warranty.txt").write_text("2029-12-31\n")
    
    (op_dir / "ip.txt").write_text("10.240.1.42\n")
    (op_dir / "os.txt").write_text("Ubuntu 24.04 LTS\n")
    (op_dir / "status.txt").write_text("IN_SERVICE\n")
    (op_dir / "rack_position.txt").write_text("RACK-04-U12\n")
    
    # Symlink to CMDB CI
    (blade_dir / "ci_link").symlink_to("../../cmdb/servers/srv-0042")

def seed_tickets_and_changes():
    """Seeds 1,000 incident tickets and scheduled changes."""
    print("[5/5] Seeding 1,000 incident tickets and scheduled changes...")
    tickets_dir = VFS_ROOT / "tickets"
    priorities = ["P1-CRITICAL", "P2-HIGH", "P3-MEDIUM", "P4-LOW"]
    states = ["NEW", "IN_PROGRESS", "RESOLVED", "CLOSED"]
    
    for i in range(1, 1001):
        t_dir = tickets_dir / f"INC-{i:04d}"
        t_dir.mkdir(parents=True, exist_ok=True)
        p = priorities[i % 4]
        s = states[(i // 4) % 4]
        (t_dir / "priority.txt").write_text(f"{p}\n")
        (t_dir / "state.txt").write_text(f"{s}\n")
        (t_dir / "short_desc.txt").write_text(f"Telemetry alert threshold breached on srv-{i:04d}\n")
        (t_dir / "affected_ci").symlink_to(f"../../cmdb/servers/srv-{i:04d}")

    # Scheduled Changes with an intentional collision
    changes_dir = VFS_ROOT / "changes" / "active"
    changes_dir.mkdir(parents=True, exist_ok=True)
    
    (changes_dir / "CHG-0101").mkdir(parents=True, exist_ok=True)
    (changes_dir / "CHG-0101" / "window.txt").write_text("2026-10-10T04:00/06:00\n")
    (changes_dir / "CHG-0101" / "affected_target").symlink_to("../../../cmdb/servers/srv-0001")
    
    (changes_dir / "CHG-0102").mkdir(parents=True, exist_ok=True)
    (changes_dir / "CHG-0102" / "window.txt").write_text("2026-10-10T04:00/06:00\n")
    (changes_dir / "CHG-0102" / "affected_target").symlink_to("../../../cmdb/servers/srv-0001")

if __name__ == "__main__":
    t0 = time.perf_counter()
    scaffold_structure()
    seed_enterprise_footprint()
    seed_bsm_tree()
    seed_service_catalog()
    seed_hardware_asset()
    seed_tickets_and_changes()
    print(f"\n[DONE] POSIX VFS ITSM Proving Grounds seeded in {time.perf_counter() - t0:.3f} seconds.")
