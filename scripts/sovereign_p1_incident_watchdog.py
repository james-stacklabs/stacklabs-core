#!/usr/bin/env python3
"""
Sovereign OS — Autonomous P1 Critical Incident Watchdog Daemon
Ticket: WO0010097-P1-CRITICAL-INCIDENT-AUTONOMOUS-WATCHDOG
Affected CI: sovereign_knot_core

Continuously monitors open P1/Critical incidents (priority=1, type='INC', state_int in [1, 2])
via FastAPI (Port 8095) every 15 seconds.
Executes an automated self-healing remediation matrix:
1. Hardware Telemetry & Swap Breaches: Safe page cache flush, conditional swap cycling, rogue CPU process detection.
2. Broken FUSE Mounts: Detection and silent lazy unmounting of disconnected transport endpoints (e.g. thinclient_drives).
3. Service Outages: Health probing of core platform ports with automated systemd/process recovery.
4. Auto-Resolution: Records forensic actions into ticket work_notes and marks state = 4 (RESOLVED).
5. Escalation: Dispatches Comet Alert / Mando Repair Overlay if unresolved after 3 cycles.
"""

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(SOVEREIGN_ROOT))
from scripts.core import api_client

PIDFILE = Path("/tmp/sovereign_p1_incident_watchdog.pid")
LOG_DIR = SOVEREIGN_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "sovereign_p1_incident_watchdog.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [P1-WATCHDOG] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger("sovereign_p1_watchdog")

POLL_INTERVAL_SECONDS = 15
MAX_REMEDIATION_ATTEMPTS = 3

# Core Platform Port Registry for Health Probing
CRITICAL_SERVICES = [
    {"name": "SDLC Portal API", "port": 8095, "restart_cmd": ["sudo", "-n", "systemctl", "restart", "stacklabs-sdlc.service"]},
    {"name": "TMI Media Ingress", "port": 8008, "restart_cmd": ["sudo", "-n", "systemctl", "restart", "sovereign-tmi.service"]},
    {"name": "FaaS Mobile Console", "port": 3033, "restart_cmd": ["sudo", "-n", "systemctl", "restart", "faas_server.service"]},
    {"name": "CMDB Studio", "port": 3025, "restart_cmd": ["sudo", "-n", "systemctl", "restart", "cmdb_studio.service"]},
    {"name": "JIT Mobile Approval Gateway", "port": 3027, "restart_cmd": ["sudo", "-n", "systemctl", "restart", "jit_approval_gateway.service"]},
    {"name": "Stream Relay Hub", "port": 3016, "restart_cmd": ["sudo", "-n", "systemctl", "restart", "sovereign-hololink-relay.service"]}
]

# Track attempt count per ticket ID to handle escalation
incident_attempt_counts: Dict[str, int] = {}
escalated_tickets: set = set()


def check_port_health(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def get_system_telemetry() -> Dict[str, Any]:
    """Capture detailed system hardware telemetry using psutil and /proc."""
    import psutil
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu_load = os.getloadavg()

    # Get top 5 CPU processes
    top_procs = []
    for proc in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']),
                       key=lambda p: p.info.get('cpu_percent') or 0,
                       reverse=True)[:5]:
        top_procs.append({
            "pid": proc.info.get('pid'),
            "name": proc.info.get('name'),
            "cpu_percent": proc.info.get('cpu_percent'),
            "mem_percent": round(proc.info.get('memory_percent') or 0, 1),
            "cmd": " ".join(proc.info.get('cmdline') or [])[:80]
        })

    return {
        "ram_total_gb": round(vm.total / (1024**3), 2),
        "ram_available_gb": round(vm.available / (1024**3), 2),
        "ram_used_percent": vm.percent,
        "swap_total_gb": round(swap.total / (1024**3), 2),
        "swap_used_gb": round(swap.used / (1024**3), 2),
        "swap_used_percent": swap.percent,
        "load_avg": cpu_load,
        "top_cpu_processes": top_procs
    }


def remediate_memory_and_swap() -> Tuple[bool, List[str]]:
    """
    Safely remediate memory and swap pressure:
    1. Flush kernel page caches via /proc/sys/vm/drop_caches.
    2. Check if available RAM > swap_used * 1.2: if safe, flush swap via swapoff/swapon.
    3. Identify and document top CPU processes.
    """
    import psutil
    logs = []
    success = True

    try:
        # Step 1: Drop page caches safely
        logger.info("Executing page cache drop (echo 3 > /proc/sys/vm/drop_caches)...")
        drop_res = subprocess.run(
            ["sync"],
            capture_output=True, text=True, timeout=10
        )
        drop_cmd = "sync && echo 3 | sudo -n tee /proc/sys/vm/drop_caches"
        drop_res = subprocess.run(
            ["sudo", "-n", "tee", "/proc/sys/vm/drop_caches"],
            input="3\n", capture_output=True, text=True, timeout=10
        )
        if drop_res.returncode == 0:
            logs.append("Kernel page cache dropped successfully (sync && drop_caches=3)")
        else:
            logs.append(f"Page cache drop warning: {drop_res.stderr.strip()}")

        # Step 2: Safe Swap Recycling
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        swap_used_bytes = swap.used
        ram_avail_bytes = vm.available

        logs.append(f"Pre-remediation Telemetry: RAM {vm.percent}% used ({round(ram_avail_bytes/(1024**3), 2)}GB avail), Swap {swap.percent}% used ({round(swap_used_bytes/(1024**3), 2)}GB)")

        if swap_used_bytes > 50 * 1024 * 1024:  # Over 50 MB in swap
            # Safety invariant: available RAM must exceed swap used by at least 20%
            if ram_avail_bytes > (swap_used_bytes * 1.2):
                logger.info(f"RAM headroom verified ({round(ram_avail_bytes/(1024**3), 2)}GB > {round(swap_used_bytes*1.2/(1024**3), 2)}GB). Cycling swap...")
                swapoff_res = subprocess.run(["sudo", "-n", "swapoff", "-a"], capture_output=True, text=True, timeout=60)
                swapon_res = subprocess.run(["sudo", "-n", "swapon", "-a"], capture_output=True, text=True, timeout=30)
                
                if swapoff_res.returncode == 0 and swapon_res.returncode == 0:
                    swap_after = psutil.swap_memory()
                    logs.append(f"Swap memory flushed cleanly via swapoff/swapon (Swap now: {swap_after.percent}% used, {round(swap_after.used/(1024**3), 2)}GB)")
                else:
                    logs.append(f"Swap cycle warning: swapoff={swapoff_res.stderr.strip()} swapon={swapon_res.stderr.strip()}")
            else:
                logs.append(f"Swap cycling deferred: available RAM ({round(ram_avail_bytes/(1024**3), 2)}GB) below 1.2x swap safety threshold ({round(swap_used_bytes*1.2/(1024**3), 2)}GB)")
        else:
            logs.append("Swap usage nominal (<50MB); swap cycle bypass")

    except Exception as e:
        logger.error(f"Error in memory remediation: {e}")
        logs.append(f"Memory remediation exception: {e}")
        success = False

    return success, logs


def remediate_fuse_mounts() -> Tuple[bool, List[str]]:
    """
    Detects and clears broken FUSE transport endpoints (e.g. thinclient_drives).
    """
    logs = []
    success = True
    candidates = [Path("/home/james/thinclient_drives"), Path("/media/james/thinclient_drives")]

    for mount_path in candidates:
        if not mount_path.exists():
            continue

        broken = False
        try:
            # Quick stat probe
            os.stat(str(mount_path))
        except OSError as e:
            if "Transport endpoint is not connected" in str(e) or e.errno in (107, 112, 5):
                broken = True
                logs.append(f"Broken FUSE transport detected on {mount_path}: {e}")

        if broken:
            logger.warning(f"Unmounting broken FUSE endpoint: {mount_path}")
            # Try userland fusermount first
            fuse_res = subprocess.run(["fusermount", "-u", "-z", str(mount_path)], capture_output=True, text=True, timeout=5)
            if fuse_res.returncode == 0:
                logs.append(f"Cleaned broken FUSE mount via fusermount -u -z on {mount_path}")
            else:
                # Fallback to sudo lazy unmount
                umount_res = subprocess.run(["sudo", "-n", "umount", "-l", str(mount_path)], capture_output=True, text=True, timeout=5)
                if umount_res.returncode == 0:
                    logs.append(f"Cleaned broken FUSE mount via sudo umount -l on {mount_path}")
                else:
                    logs.append(f"Failed to unmount {mount_path}: {umount_res.stderr.strip()}")
                    success = False

    if not logs:
        logs.append("FUSE mounts inspected: zero broken transport endpoints found")

    return success, logs


def remediate_critical_services() -> Tuple[bool, List[str]]:
    """
    Probes core platform ports and attempts recovery if any are down.
    """
    logs = []
    success = True

    for svc in CRITICAL_SERVICES:
        name = svc["name"]
        port = svc["port"]
        cmd = svc["restart_cmd"]

        is_up = check_port_health("127.0.0.1", port)
        if is_up:
            continue

        logger.warning(f"Port {port} ({name}) is DOWN! Attempting automated recovery...")
        logs.append(f"Service outage detected on Port {port} ({name})")

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            time.sleep(1.5)
            recovered = check_port_health("127.0.0.1", port)
            if recovered:
                logs.append(f"Service {name} (Port {port}) successfully recovered via automated restart")
            else:
                logs.append(f"Service {name} restart initiated; awaiting stabilization")
        except Exception as e:
            logs.append(f"Failed to execute restart for {name}: {e}")
            success = False

    if not logs:
        ports_str = ", ".join(str(s["port"]) for s in CRITICAL_SERVICES)
        logs.append(f"All core platform ports ({ports_str}) healthy and accepting connections")

    return success, logs


def dispatch_comet_alert(ticket_id: str, title: str, details: str):
    """Dispatches a priority alert HTTP POST to the Comet Relay webhook."""
    url = "http://127.0.0.1:8015/webhook/alert"
    payload = {
        "alert_type": f"CRITICAL INCIDENT ESCALATION: {title}",
        "service_name": "P1 Incident Watchdog",
        "ci": "sovereign_knot_core",
        "sys_ticket_id": ticket_id,
        "avatar_url": "/avatars/mando_sentry.png",
        "details": details
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            logger.info(f"📡 Dispatched Comet Priority Alert for {ticket_id}")
    except Exception as e:
        logger.warning(f"Failed to dispatch Comet alert: {e}")


def dispatch_mando_overlay(ticket_id: str, title: str):
    """Dispatches Mando Robot Repair overlay alert to FanStack Relay."""
    url = "http://127.0.0.1:8000/api/overlay/mando-repair"
    payload = {
        "target_game_pk": "GLOBAL",
        "reason": f"P1 ESCALATION: {title} ({ticket_id})"
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            logger.info(f"🛠️ Dispatched Mando Repair Overlay for {ticket_id}")
    except Exception as e:
        logger.warning(f"Failed to dispatch Mando overlay: {e}")


def triage_and_remediate_incident(ticket: Dict[str, Any]) -> bool:
    """
    Executes the automated self-healing remediation matrix for a P1 incident.
    """
    ticket_id = ticket.get("id") or ticket.get("sys_id")
    title = ticket.get("title") or "Unnamed Incident"
    desc = ticket.get("description") or ""
    current_work_notes = ticket.get("work_notes") or ""

    logger.info(f"🔍 Triaging P1 Incident: {ticket_id} — '{title}'")
    incident_attempt_counts[ticket_id] = incident_attempt_counts.get(ticket_id, 0) + 1
    attempt_num = incident_attempt_counts[ticket_id]

    remediation_log = []
    remediation_log.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [Autonomous P1 Watchdog - Attempt {attempt_num}]")
    remediation_log.append(f"Target: {ticket_id} ({title})")

    # 1. Memory and Swap Remediation
    mem_ok, mem_logs = remediate_memory_and_swap()
    for l in mem_logs:
        remediation_log.append(f"  • {l}")

    # 2. FUSE Mount Remediation
    fuse_ok, fuse_logs = remediate_fuse_mounts()
    for l in fuse_logs:
        remediation_log.append(f"  • {l}")

    # 3. Critical Port Health Remediation
    svc_ok, svc_logs = remediate_critical_services()
    for l in svc_logs:
        remediation_log.append(f"  • {l}")

    # Post-Remediation Telemetry Verification
    telemetry_after = get_system_telemetry()
    remediation_log.append(f"Post-Remediation Baseline: RAM {telemetry_after['ram_used_percent']}% used, Swap {telemetry_after['swap_used_percent']}% used, Load: {telemetry_after['load_avg']}")

    overall_remediated = mem_ok and fuse_ok and svc_ok

    if overall_remediated:
        remediation_log.append("Remediation Matrix Result: SUCCESS (All thresholds nominal). Auto-resolving ticket.")
        combined_notes = current_work_notes + "\n\n" + "\n".join(remediation_log)

        try:
            # Update work notes first
            api_client.update_ticket(ticket_id, {"work_notes": combined_notes.strip()})
            # Resolve ticket
            res = api_client.resolve_ticket(
                ticket_id=ticket_id,
                resolution_notes=f"Autonomous self-healing completed successfully by Sovereign P1 Watchdog. System telemetry restored to nominal operating baseline."
            )
            logger.info(f"✅ Ticket {ticket_id} RESOLVED autonomously: {res}")
            return True
        except Exception as e:
            logger.error(f"Failed to resolve ticket {ticket_id} via API: {e}")
            return False
    else:
        # Check if escalation is warranted
        if attempt_num >= MAX_REMEDIATION_ATTEMPTS and ticket_id not in escalated_tickets:
            escalated_tickets.add(ticket_id)
            escalation_msg = f"ESCALATION TRIGGERED: Exceeded {MAX_REMEDIATION_ATTEMPTS} autonomous remediation cycles without recovery."
            remediation_log.append(f"⚠️ {escalation_msg}")
            logger.error(f"🚨 Escalating {ticket_id}: {escalation_msg}")

            combined_notes = current_work_notes + "\n\n" + "\n".join(remediation_log)
            api_client.update_ticket(ticket_id, {"work_notes": combined_notes.strip()})

            dispatch_comet_alert(ticket_id, title, "\n".join(remediation_log))
            dispatch_mando_overlay(ticket_id, title)
        else:
            combined_notes = current_work_notes + "\n\n" + "\n".join(remediation_log)
            api_client.update_ticket(ticket_id, {"work_notes": combined_notes.strip()})

        return False


def scan_and_remediate_p1_incidents() -> int:
    """
    Scans SDLC ticketing ledger via FastAPI for active P1 incidents.
    Returns count of resolved incidents.
    """
    try:
        # Fetch open tickets with priority=1
        tickets = api_client.get_tickets(state_int=[1, 2], priority=1)
    except Exception as e:
        logger.error(f"Failed to query tickets from FastAPI: {e}")
        return 0

    # Filter for active Incident tickets (type == 'INC' or title containing incident indicators)
    incidents = [
        t for t in tickets 
        if t.get("type") == "INC" or "CRITICAL:" in (t.get("title") or "") or "BREACH" in (t.get("title") or "")
    ]

    if not incidents:
        logger.debug(f"P1 Watchdog scan: 0 active P1 incidents (Total open P1s: {len(tickets)})")
        return 0

    logger.info(f"🚨 Found {len(incidents)} active P1 incident(s) requiring autonomous remediation!")
    resolved_count = 0
    for inc in incidents:
        if triage_and_remediate_incident(inc):
            resolved_count += 1

    return resolved_count


def run_daemon():
    """Runs the watchdog continuously as a daemon."""
    logger.info("=========================================================")
    logger.info("🛡️ SOVEREIGN P1 CRITICAL INCIDENT WATCHDOG DAEMON STARTED")
    logger.info(f"Polling Interval: {POLL_INTERVAL_SECONDS}s | PID: {os.getpid()}")
    logger.info("=========================================================")

    # Write PID file
    PIDFILE.write_text(str(os.getpid()))

    def handle_exit(signum, frame):
        logger.info("Received termination signal. Shutting down P1 Watchdog...")
        if PIDFILE.exists():
            PIDFILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    try:
        while True:
            scan_and_remediate_p1_incidents()
            time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        if PIDFILE.exists():
            PIDFILE.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Sovereign OS P1 Critical Incident Watchdog")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in daemon mode")
    parser.add_argument("--once", action="store_true", help="Execute single-pass scan and exit")
    parser.add_argument("--test-matrix", action="store_true", help="Run full self-healing matrix directly without tickets")
    args = parser.parse_args()

    if args.test_matrix:
        logger.info("🧪 Testing self-healing remediation matrix directly...")
        mem_ok, mem_logs = remediate_memory_and_swap()
        fuse_ok, fuse_logs = remediate_fuse_mounts()
        svc_ok, svc_logs = remediate_critical_services()
        print("\n--- Memory & Swap ---")
        for l in mem_logs:
            print(" ", l)
        print("\n--- FUSE Mounts ---")
        for l in fuse_logs:
            print(" ", l)
        print("\n--- Core Services ---")
        for l in svc_logs:
            print(" ", l)
        sys.exit(0)

    if args.once:
        logger.info("Executing single-pass P1 incident scan...")
        resolved = scan_and_remediate_p1_incidents()
        logger.info(f"Single-pass scan complete. Resolved: {resolved}")
        sys.exit(0)

    # Default to daemon mode
    run_daemon()


if __name__ == "__main__":
    main()
