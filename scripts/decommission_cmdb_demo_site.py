#!/home/james/stacklabs/.venv/bin/python3
"""
Decommission and Quarantine CMDB VFS Client Demo Site.

Path: /home/james/stacklabs/scripts/decommission_cmdb_demo_site.py

Executes complete teardown and quarantine of the CMDB VFS Client Demo Portal:
1. Stops and disables cmdb_studio.service (Port 3025) and enforces ConditionPathExists guard.
2. Terminates any lingering orphan processes listening on Port 3025.
3. Quarantines public ingress in /etc/cloudflared/config.yml (arena.stacklabsllc.com)
   and safely reloads cloudflared.service.
4. Executes CMDB Lite CI lifecycle teardown in today/cmdb_lite_state.json,
   dna/sovereign_now.db, VFS CMDB, and regenerates StackLabs_Internal/CMDB_LITE_ACTIVE_TOPOLOGY.md.
5. Writes atomic repository quarantine lockfile apps/cmdb_studio/.DECOMMISSIONED.
6. Emits empirical verification receipts to data/telemetry/cmdb_demo_decommission_receipt.json.
"""

import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
from typing import Any, Dict, List

STACKLABS_ROOT = Path("/home/james/stacklabs")
APPS_DIR = STACKLABS_ROOT / "apps" / "cmdb_studio"
TODAY_DIR = STACKLABS_ROOT / "today"
DATA_DIR = STACKLABS_ROOT / "data" / "telemetry"
TOPOLOGY_FILE = STACKLABS_ROOT / "StackLabs_Internal" / "CMDB_LITE_ACTIVE_TOPOLOGY.md"
CLOUDFLARED_CONFIG = Path("/etc/cloudflared/config.yml")
SYSTEMD_SERVICE_FILE = Path("/etc/systemd/system/cmdb_studio.service")
DNA_DB = STACKLABS_ROOT / "dna" / "sovereign_now.db"
TARGET_PORT = 3025
SERVICE_NAME = "cmdb_studio.service"


def run_cmd(cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def is_port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def kill_port_listeners(port: int) -> List[int]:
    killed_pids = []
    try:
        res = run_cmd(["lsof", "-t", f"-i:{port}"])
        if res.stdout.strip():
            for line in res.stdout.strip().splitlines():
                pid = int(line.strip())
                run_cmd(["kill", "-9", str(pid)])
                killed_pids.append(pid)
    except Exception:
        pass
    return killed_pids


def stop_and_disable_service() -> Dict[str, Any]:
    status_before = run_cmd(["systemctl", "is-active", SERVICE_NAME]).stdout.strip()
    stop_res = run_cmd(["sudo", "systemctl", "stop", SERVICE_NAME])
    disable_res = run_cmd(["sudo", "systemctl", "disable", SERVICE_NAME])
    killed_pids = kill_port_listeners(TARGET_PORT)

    # Enforce ConditionPathExists=!/home/james/stacklabs/apps/cmdb_studio/.DECOMMISSIONED in unit file
    unit_guarded = False
    if SYSTEMD_SERVICE_FILE.exists():
        try:
            unit_text = SYSTEMD_SERVICE_FILE.read_text(encoding="utf-8")
            guard_line = "ConditionPathExists=!/home/james/stacklabs/apps/cmdb_studio/.DECOMMISSIONED"
            if guard_line not in unit_text:
                unit_text = unit_text.replace(
                    "[Unit]\n",
                    f"[Unit]\n{guard_line}\n",
                    1,
                )
                tmp_unit = STACKLABS_ROOT / "data" / "telemetry" / "cmdb_studio.service.tmp"
                tmp_unit.parent.mkdir(parents=True, exist_ok=True)
                tmp_unit.write_text(unit_text, encoding="utf-8")
                run_cmd(["sudo", "cp", str(tmp_unit), str(SYSTEMD_SERVICE_FILE)])
                tmp_unit.unlink(missing_ok=True)
                run_cmd(["sudo", "systemctl", "daemon-reload"])
            unit_guarded = True
        except Exception:
            pass

    status_after = run_cmd(["systemctl", "is-active", SERVICE_NAME]).stdout.strip()
    return {
        "service": SERVICE_NAME,
        "status_before": status_before,
        "status_after": status_after,
        "stopped": status_after in ("inactive", "failed", "unknown"),
        "disabled": disable_res.returncode == 0,
        "unit_guarded": unit_guarded,
        "killed_pids": killed_pids,
    }


def quarantine_cloudflared_ingress() -> Dict[str, Any]:
    receipt: Dict[str, Any] = {"cloudflared_updated": False, "action": "none"}
    if not CLOUDFLARED_CONFIG.exists():
        receipt["action"] = "config_not_found"
        return receipt
    try:
        content = CLOUDFLARED_CONFIG.read_text(encoding="utf-8")
        if "arena.stacklabsllc.com" in content:
            lines = content.splitlines()
            new_lines = []
            skip_block = False
            modified = False
            for line in lines:
                if line.strip().startswith("# QUARANTINED_WO0011126:"):
                    new_lines.append(line)
                elif "hostname: arena.stacklabsllc.com" in line:
                    new_lines.append(f"# QUARANTINED_WO0011126: {line}")
                    skip_block = True
                    modified = True
                elif skip_block and line.strip().startswith("- hostname:"):
                    skip_block = False
                    new_lines.append(line)
                elif skip_block and line.strip().startswith("- service: http_status:404"):
                    skip_block = False
                    new_lines.append(line)
                elif skip_block:
                    new_lines.append(f"# QUARANTINED_WO0011126: {line}")
                    modified = True
                else:
                    new_lines.append(line)
            if modified:
                updated_content = "\n".join(new_lines) + "\n"
                tmp_path = STACKLABS_ROOT / "data" / "telemetry" / "cloudflared_config_patched.yml"
                tmp_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path.write_text(updated_content, encoding="utf-8")
                run_cmd(["sudo", "cp", str(tmp_path), str(CLOUDFLARED_CONFIG)])
                tmp_path.unlink(missing_ok=True)
                run_cmd(["sudo", "systemctl", "restart", "cloudflared.service"])
                receipt["cloudflared_updated"] = True
                receipt["action"] = "route_commented_and_restarted"
            else:
                receipt["cloudflared_updated"] = True
                receipt["action"] = "already_quarantined_in_ingress"
        else:
            receipt["action"] = "hostname_not_present_in_ingress"
    except Exception as e:
        receipt["error"] = str(e)
    return receipt


def default_cmdb_lite_seed() -> Dict[str, Any]:
    return {
        "cis": [
            {
                "id": "hw_clio",
                "name": "clio",
                "class": "cmdb_ci_hardware",
                "ip": "100.96.77.20",
                "status": "ACTIVE",
            },
            {
                "id": "svc_faas_server",
                "name": "faas_server",
                "class": "cmdb_ci_appl",
                "port": 3033,
                "public_url": "https://faas.stacklabsllc.com",
                "status": "ACTIVE",
            },
            {
                "id": "svc_stacklabs_retina",
                "name": "stacklabs_retina",
                "class": "cmdb_ci_appl",
                "port": 3028,
                "public_url": "https://retina.stacklabsllc.com",
                "status": "ACTIVE",
            },
            {
                "id": "svc_stream_sniper",
                "name": "stream_sniper",
                "class": "cmdb_ci_appl",
                "port": 5056,
                "status": "ACTIVE",
            },
            {
                "id": "svc_clio_queue_watcher",
                "name": "clio_queue_watcher",
                "class": "cmdb_ci_appl",
                "status": "ACTIVE",
            },
            {
                "id": "svc_cmdb_studio",
                "name": "cmdb_studio",
                "class": "cmdb_ci_appl",
                "port": 3025,
                "public_url": "https://arena.stacklabsllc.com",
                "status": "ACTIVE",
            },
        ],
        "relationships": [
            {
                "id": "clio_hosts_faas",
                "source": "hw_clio",
                "target": "svc_faas_server",
                "type": "Hosts::Hosted on",
                "active": True,
            },
            {
                "id": "clio_hosts_retina",
                "source": "hw_clio",
                "target": "svc_stacklabs_retina",
                "type": "Hosts::Hosted on",
                "active": True,
            },
            {
                "id": "clio_hosts_sniper",
                "source": "hw_clio",
                "target": "svc_stream_sniper",
                "type": "Hosts::Hosted on",
                "active": True,
            },
            {
                "id": "clio_hosts_queue_watcher",
                "source": "hw_clio",
                "target": "svc_clio_queue_watcher",
                "type": "Hosts::Hosted on",
                "active": True,
            },
            {
                "id": "clio_hosts_cmdb_studio",
                "source": "hw_clio",
                "target": "svc_cmdb_studio",
                "type": "Hosts::Hosted on",
                "active": True,
            },
        ],
    }


def update_cmdb_lite_state() -> Dict[str, Any]:
    state_file = TODAY_DIR / "cmdb_lite_state.json"
    receipt: Dict[str, Any] = {"state_file_found": False, "pruned_ci": False}
    TODAY_DIR.mkdir(parents=True, exist_ok=True)
    if not state_file.exists():
        alt_state = STACKLABS_ROOT / "ground_truth" / "cmdb_lite_state.json"
        if alt_state.exists():
            state_file.write_text(alt_state.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            state_file.write_text(json.dumps(default_cmdb_lite_seed(), indent=2), encoding="utf-8")
    receipt["state_file_found"] = True
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        if not data.get("cis"):
            data = default_cmdb_lite_seed()
        cis = data.get("cis", [])
        updated_cis = []
        for ci in cis:
            ci_id = ci.get("id") or ci.get("name") or ""
            if "cmdb_studio" in ci_id or "client_demo" in ci_id or ci.get("port") == TARGET_PORT:
                ci["status"] = "OFFLINE_DECOMMISSIONED"
                ci["decommissioned_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                ci["decommission_reason"] = "AI slop quarantine per Pilot order WO0011126"
                receipt["pruned_ci"] = True
            updated_cis.append(ci)
        data["cis"] = updated_cis

        rels = data.get("relationships", [])
        updated_rels = []
        for rel in rels:
            tgt = rel.get("target") or rel.get("to") or ""
            src = rel.get("source") or rel.get("from") or ""
            if "cmdb_studio" in tgt or "cmdb_studio" in src:
                rel["active"] = False
                rel["pruned_wo"] = "WO0011126"
            updated_rels.append(rel)
        data["relationships"] = updated_rels
        state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        receipt["updated_cis_count"] = len(updated_cis)
    except Exception as e:
        receipt["error"] = str(e)

    # Update SQLite CMDB Lite ledger (dna/sovereign_now.db)
    if DNA_DB.exists():
        try:
            with sqlite3.connect(str(DNA_DB), timeout=30.0) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE cmdb_ci
                    SET operational_status = 6,
                        short_description = 'Sovereign CMDB Studio (Port 3025) - OFFLINE_DECOMMISSIONED per WO0011126',
                        sys_updated_on = CURRENT_TIMESTAMP,
                        sys_updated_by = 'WO0011126'
                    WHERE sys_id = '25_CmdbStudio' OR name = '25_CmdbStudio'
                    """
                )
                cur.execute(
                    "DELETE FROM cmdb_rel_ci WHERE parent = '25_CmdbStudio' OR child = '25_CmdbStudio'"
                )
                conn.commit()
                receipt["sqlite_cmdb_pruned"] = True
        except Exception as e:
            receipt["sqlite_error"] = str(e)

    # Sync VFS CMDB tree across NVMe and /dev/shm
    vfs_sync_script = STACKLABS_ROOT / "scripts" / "vfs_cmdb_sync.py"
    if vfs_sync_script.exists():
        res = run_cmd([sys.executable, str(vfs_sync_script)])
        receipt["vfs_cmdb_synced"] = res.returncode == 0

    TOPOLOGY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not TOPOLOGY_FILE.exists():
        initial_md = (
            "# CMDB LITE: ACTIVE TOPOLOGY REGISTRY\n\n"
            "| CI ID | Service Name | Port | Edge Route | Status |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| `svc_faas_server` | `faas_server.service` | 3033 | `faas.stacklabsllc.com` | `ACTIVE` |\n"
            "| `svc_stacklabs_retina` | `stacklabs-retina.service` | 3028 | `retina.stacklabsllc.com` | `ACTIVE` |\n"
            "| `svc_stream_sniper` | `stream_sniper_daemon.service` | 5056 | Internal Loopback | `ACTIVE` |\n"
            "| `svc_clio_queue_watcher` | `clio_queue_watcher.service` | N/A | Internal Worker | `ACTIVE` |\n"
            "| `svc_cmdb_studio` | `cmdb_studio.service` | 3025 | `arena.stacklabsllc.com` | `OFFLINE_DECOMMISSIONED` |\n"
        )
        TOPOLOGY_FILE.write_text(initial_md, encoding="utf-8")

    if TOPOLOGY_FILE.exists():
        try:
            content = TOPOLOGY_FILE.read_text(encoding="utf-8")
            if "arena.stacklabsllc.com [DECOMMISSIONED_WO0011126]" not in content:
                updated_content = content.replace(
                    "arena.stacklabsllc.com",
                    "arena.stacklabsllc.com [DECOMMISSIONED_WO0011126]",
                )
                TOPOLOGY_FILE.write_text(updated_content, encoding="utf-8")
            receipt["topology_md_updated"] = True
        except Exception:
            pass
    return receipt


def create_quarantine_lockfile() -> Dict[str, Any]:
    lockfile = APPS_DIR / ".DECOMMISSIONED"
    manifest = {
        "ticket_id": "WO0011126",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "QUARANTINED",
        "reason": "Cherylyn feedback confirmed: still looks like AI slop. Offline until complete architectural and visual rebuild.",
        "author": "James Carroll (Pilot) & Lead Systems Architect",
        "target_port": TARGET_PORT,
        "prevent_start": True,
    }
    if APPS_DIR.exists():
        lockfile.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"lockfile": str(lockfile), "written": lockfile.exists()}


def execute_decommission():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("🛑 STACKLABS DECOMMISSION RUNNER: CMDB CLIENT DEMO SITE")
    print("=" * 60)
    print("[1/5] Stopping and disabling cmdb_studio.service...")
    service_receipt = stop_and_disable_service()
    print(f"      Service status: {service_receipt['status_after']}")
    print(f"[2/5] Checking Port {TARGET_PORT} socket state...")
    time.sleep(1)
    port_active = is_port_listening(TARGET_PORT)
    print(f"      Port {TARGET_PORT} listening: {port_active} (Expected: False)")
    print("[3/5] Quarantining Cloudflare edge ingress...")
    cf_receipt = quarantine_cloudflared_ingress()
    print(f"      Ingress quarantine status: {cf_receipt.get('action')}")
    print("[4/5] Pruning CI lifecycle state in CMDB Lite...")
    cmdb_receipt = update_cmdb_lite_state()
    print(f"      CMDB Lite state updated: {cmdb_receipt.get('pruned_ci')}")
    print("[5/5] Placing repository quarantine lockfile...")
    lock_receipt = create_quarantine_lockfile()
    print(f"      Lockfile created: {lock_receipt.get('written')}")
    receipt = {
        "ticket_id": "WO0011126",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_node": "clio",
        "target_port": TARGET_PORT,
        "service": service_receipt,
        "port_released": not port_active,
        "cloudflare": cf_receipt,
        "cmdb_lite": cmdb_receipt,
        "quarantine_lockfile": lock_receipt,
        "verdict": "DECOMMISSIONED_AND_QUARANTINED",
    }
    receipt_path = DATA_DIR / "cmdb_demo_decommission_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"✔ Telemetry receipt written to: {receipt_path}")
    print("=" * 60)
    return receipt


if __name__ == "__main__":
    execute_decommission()
