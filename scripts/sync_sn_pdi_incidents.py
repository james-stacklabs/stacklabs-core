#!/usr/bin/env python3
"""
Sovereign OS: Ingest ServiceNow PDI Live Incidents to VFS
Path: /home/james/stacklabs/scripts/sync_sn_pdi_incidents.py
Author: James Carroll (Pilot) & Lead Systems Architect
"""
import os
import requests
import json
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path("/home/james/stacklabs/.env"))

SN_INSTANCE = os.getenv("SN_INSTANCE", "https://dev186522.service-now.com")
SN_USER = os.getenv("SN_USER", "admin")
SN_PASS = os.getenv("SN_PASS", "J-Slf7SPmg!2")

VFS_TICKETS_NVME = Path("/home/james/stacklabs/vfs/tickets")
VFS_TICKETS_SHM = Path("/dev/shm/faas_vfs/tickets")
VFS_CMDB = Path("/home/james/stacklabs/vfs/cmdb")

def ingest_incidents():
    print(f"[1/3] Connecting to ServiceNow PDI: {SN_INSTANCE}...")
    url = f"{SN_INSTANCE}/api/now/table/incident?sysparm_fields=sys_id,number,short_description,priority,state,cmdb_ci,sys_created_on,urgency,impact&sysparm_limit=50"
    
    t0 = time.perf_counter()
    res = requests.get(url, auth=(SN_USER, SN_PASS), timeout=15)
    if res.status_code != 200:
        raise RuntimeError(f"ServiceNow REST query failed with status {res.status_code}: {res.text}")
        
    incidents = res.json().get("result", [])
    fetch_elapsed_ms = (time.perf_counter() - t0) * 1000.0
    print(f"      Fetched {len(incidents)} live incident records in {fetch_elapsed_ms:.2f} ms.")

    # Scaffolding directories
    for root in [VFS_TICKETS_NVME, VFS_TICKETS_SHM]:
        root.mkdir(parents=True, exist_ok=True)

    print("[2/3] Materializing incident records to VFS dual-plane (NVMe & /dev/shm)...")
    linked_ci_count = 0

    for inc in incidents:
        num = inc.get("number", "UNKNOWN")
        sys_id = inc.get("sys_id", "")
        prio = inc.get("priority", "3")
        state = inc.get("state", "1")
        desc = inc.get("short_description", "")
        created = inc.get("sys_created_on", "")
        
        ci_raw = inc.get("cmdb_ci", "")
        ci_sys_id = ci_raw.get("value", "") if isinstance(ci_raw, dict) else str(ci_raw)

        for base in [VFS_TICKETS_NVME, VFS_TICKETS_SHM]:
            inc_dir = base / num
            inc_dir.mkdir(parents=True, exist_ok=True)
            
            (inc_dir / "number.txt").write_text(f"{num}\n")
            (inc_dir / "sys_id.txt").write_text(f"{sys_id}\n")
            (inc_dir / "priority.txt").write_text(f"{prio}\n")
            (inc_dir / "state.txt").write_text(f"{state}\n")
            (inc_dir / "short_description.txt").write_text(f"{desc}\n")
            (inc_dir / "created_at.txt").write_text(f"{created}\n")
            
            # Map CI link
            aff_link = inc_dir / "affected_ci"
            if aff_link.is_symlink() or aff_link.exists():
                aff_link.unlink()
                
            if ci_sys_id:
                # Store sys_id leaf
                (inc_dir / "cmdb_ci_sys_id.txt").write_text(f"{ci_sys_id}\n")
                
                # Try finding matching server or app in local VFS CMDB
                matched_ci = None
                if (VFS_CMDB / "physical").exists():
                    for srv in (VFS_CMDB / "physical").iterdir():
                        if srv.is_dir() and (srv / "sys_id.txt").exists():
                            if (srv / "sys_id.txt").read_text().strip() == ci_sys_id:
                                matched_ci = srv
                                break
                                
                if matched_ci:
                    aff_link.symlink_to(matched_ci)
                    linked_ci_count += 1
                else:
                    # Generic placeholder CI reference
                    (inc_dir / "ci_name.txt").write_text(f"sys_id:{ci_sys_id}\n")

    print(f"[3/3] Ingestion complete. Projected {len(incidents)} tickets to VFS.")
    return len(incidents)

if __name__ == "__main__":
    count = ingest_incidents()
    print(f"[DONE] Successfully synchronized {count} live ServiceNow incidents to VFS.")
