#!/usr/bin/env python3
"""
StackLabs Platform: ServiceNow Sample CIs to Sysfs VFS CMDB Projector
Materializes demo enterprise CIs and relationships from ServiceNow PDI into POSIX VFS.

Target Roots:
- Persistent NVMe: /home/james/stacklabs/vfs/cmdb
- Volatile Pagecache: /dev/shm/faas_vfs/cmdb
"""
import os
import sys
import shutil
import requests
from pathlib import Path

# Configuration & PDI Credentials
SN_INSTANCE = os.getenv("SN_INSTANCE", "https://dev186522.service-now.com")
SN_USER = os.getenv("SN_USER", "admin")
SN_PASS = os.getenv("SN_PASS", "J-Slf7SPmg!2")
AUTH = (SN_USER, SN_PASS)

TARGET_ROOTS = [
    Path("/home/james/stacklabs/vfs/cmdb"),
    Path("/dev/shm/faas_vfs/cmdb")
]

# Invariant 1.3: Non-destructive coexistence with existing local hardware and services
LOCAL_PROTECTED_PHYSICAL = {"clio", "artemis", "c120", "argo", "pegasus"}
LOCAL_PROTECTED_LOGICAL = {"clio_queue_watcher", "cmdb_studio", "faas_server", "stacklabs_retina", "stream_sniper"}

def clean_slug(val: str) -> str:
    """Normalize ServiceNow CI display names into safe POSIX directory slugs."""
    if not val:
        return "unnamed"
    slug = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(val).strip().lower())
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")

def write_scalar(filepath: Path, content: str):
    """Write an atomic 1-line scalar text attribute."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(str(content).strip() + "\n", encoding="utf-8")

def create_relative_symlink(source_dir: Path, link_path: Path):
    """Create a relative POSIX symlink pointing from link_path to source_dir."""
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.is_symlink() or link_path.is_file():
        link_path.unlink()
    elif link_path.is_dir():
        shutil.rmtree(link_path)
    rel_target = os.path.relpath(source_dir, link_path.parent)
    link_path.symlink_to(rel_target)

def sync_sn_to_vfs_root(root: Path):
    print(f"\n==================================================================")
    print(f"⚡ MATERIALIZING SERVICENOW ENTERPRISE CIs TO: {root}")
    print(f"==================================================================")
    root.mkdir(parents=True, exist_ok=True)
    phys_root = root / "physical"
    log_root = root / "logical"
    phys_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # 1. Physical Servers (cmdb_ci_server)
    # -------------------------------------------------------------
    print("1. Fetching Server CIs from ServiceNow (cmdb_ci_server)...")
    url_srv = f"{SN_INSTANCE}/api/now/table/cmdb_ci_server?sysparm_limit=50&sysparm_fields=sys_id,name,ip_address,os,operational_status,ram,cpu_count"
    try:
        r_srv = requests.get(url_srv, auth=AUTH, timeout=15)
        r_srv.raise_for_status()
        servers = r_srv.json().get("result", [])
    except Exception as e:
        print(f"❌ Failed to query ServiceNow servers: {e}")
        return False

    server_lookup = {}
    projected_servers = 0
    for srv in servers:
        sys_id = srv.get("sys_id")
        raw_name = srv.get("name")
        if not raw_name:
            continue
        name = clean_slug(raw_name)
        server_lookup[sys_id] = name
        
        target_dir = phys_root / name
        
        # Enforce non-destructive write invariant on local metal nodes
        if name in LOCAL_PROTECTED_PHYSICAL or (target_dir.exists() and not (target_dir / "source.txt").exists()):
            print(f"  [-] Preserving local hardware node: {name}")
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        write_scalar(target_dir / "id.txt", sys_id)
        write_scalar(target_dir / "name.txt", raw_name)
        write_scalar(target_dir / "class.txt", "cmdb_ci_server")
        write_scalar(target_dir / "ip.txt", srv.get("ip_address") or "0.0.0.0")
        write_scalar(target_dir / "os.txt", srv.get("os") or "Linux")
        write_scalar(target_dir / "status.txt", srv.get("operational_status") or "1")
        write_scalar(target_dir / "ram_mb.txt", srv.get("ram") or "16384")
        write_scalar(target_dir / "cpus.txt", srv.get("cpu_count") or "4")
        write_scalar(target_dir / "source.txt", "servicenow_pdi_dev186522")
        projected_servers += 1

    print(f"  [+] Projected {projected_servers} Physical Server CIs into {phys_root} ({len(server_lookup)} total indexed)")

    # -------------------------------------------------------------
    # 2. Logical Applications (cmdb_ci_appl)
    # -------------------------------------------------------------
    print("2. Fetching Application CIs from ServiceNow (cmdb_ci_appl)...")
    url_app = f"{SN_INSTANCE}/api/now/table/cmdb_ci_appl?sysparm_limit=50&sysparm_fields=sys_id,name,tcp_port,operational_status,version"
    try:
        r_app = requests.get(url_app, auth=AUTH, timeout=15)
        r_app.raise_for_status()
        apps = r_app.json().get("result", [])
    except Exception as e:
        print(f"❌ Failed to query ServiceNow applications: {e}")
        return False

    app_lookup = {}
    projected_apps = 0
    for app in apps:
        sys_id = app.get("sys_id")
        raw_name = app.get("name")
        if not raw_name:
            continue
        name = clean_slug(raw_name)
        app_lookup[sys_id] = name
        
        target_dir = log_root / name
        
        # Enforce non-destructive write invariant on local platform services
        if name in LOCAL_PROTECTED_LOGICAL or (target_dir.exists() and not (target_dir / "source.txt").exists()):
            print(f"  [-] Preserving local platform service: {name}")
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        write_scalar(target_dir / "id.txt", sys_id)
        write_scalar(target_dir / "name.txt", raw_name)
        write_scalar(target_dir / "class.txt", "cmdb_ci_appl")
        write_scalar(target_dir / "port.txt", app.get("tcp_port") or "80")
        write_scalar(target_dir / "status.txt", app.get("operational_status") or "1")
        write_scalar(target_dir / "version.txt", app.get("version") or "1.0.0")
        write_scalar(target_dir / "source.txt", "servicenow_pdi_dev186522")
        projected_apps += 1

    print(f"  [+] Projected {projected_apps} Logical Application CIs into {log_root} ({len(app_lookup)} total indexed)")

    # -------------------------------------------------------------
    # 3. Relationships (cmdb_rel_ci: Runs on::Hosts)
    # -------------------------------------------------------------
    print("3. Resolving Relationships as Native POSIX Symlinks (cmdb_rel_ci)...")
    url_rel = f"{SN_INSTANCE}/api/now/table/cmdb_rel_ci?sysparm_limit=250&sysparm_fields=sys_id,parent,child,type"
    try:
        r_rel = requests.get(url_rel, auth=AUTH, timeout=15)
        r_rel.raise_for_status()
        rels = r_rel.json().get("result", [])
    except Exception as e:
        print(f"❌ Failed to query ServiceNow relationships: {e}")
        return False

    linked_count = 0
    for rel in rels:
        parent_id = rel.get("parent", {}).get("value")
        child_id = rel.get("child", {}).get("value")
        
        # Direction 1: Child is application and parent is server (Runs on::Hosts)
        if child_id in app_lookup and parent_id in server_lookup:
            app_name = app_lookup[child_id]
            srv_name = server_lookup[parent_id]
            
            if app_name not in LOCAL_PROTECTED_LOGICAL:
                app_dir = log_root / app_name
                srv_dir = phys_root / srv_name
                link_path = app_dir / "runs_on"
                
                create_relative_symlink(srv_dir, link_path)
                linked_count += 1

        # Direction 2: Parent is application and child is server (Runs on::Runs)
        elif parent_id in app_lookup and child_id in server_lookup:
            app_name = app_lookup[parent_id]
            srv_name = server_lookup[child_id]
            
            if app_name not in LOCAL_PROTECTED_LOGICAL:
                app_dir = log_root / app_name
                srv_dir = phys_root / srv_name
                link_path = app_dir / "runs_on"
                
                if not link_path.exists():
                    create_relative_symlink(srv_dir, link_path)
                    linked_count += 1

    print(f"  [⮑ ] Materialized {linked_count} native relative symlinks in {log_root}")
    return True

def main():
    print("🚀 [STACKLABS VFS CMDB] Synchronizing ServiceNow Enterprise Sample CIs...")
    success_all = True
    for root in TARGET_ROOTS:
        ok = sync_sn_to_vfs_root(root)
        if not ok:
            success_all = False
            
    if success_all:
        print("\n✅ [SUCCESS] ServiceNow enterprise sample topology projected to VFS CMDB.")
        sys.exit(0)
    else:
        print("\n⚠️ [WARNING] One or more VFS targets failed synchronization.")
        sys.exit(1)

if __name__ == "__main__":
    main()
