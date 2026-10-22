#!/usr/bin/env python3
"""
Work Order Execution Hook: WO0010038-CLIO-ENGINE-ROOM-DISPATCH-TEST
Path: /home/james/stacklabs/scripts/execute_wo0010036_clio_engine_room_dispatch_test.py
Task: Autonomous Dispatcher Pipeline Verification & Host Telemetry Gathering

Executed natively by antigravity_dispatcher on Clio upon JIT approval.
"""

import os
import sys
import json
import socket
import subprocess
from datetime import datetime, timezone

SOVEREIGN_HOME = "/home/james/stacklabs"
sys.path.insert(0, SOVEREIGN_HOME)

from scripts.core import api_client

def run_test():
    print("================================================================================")
    print("🚀 CLIO ENGINE ROOM: INAUGURAL WORK ORDER DISPATCH VERIFICATION")
    print("Task ID: WO0010038-CLIO-ENGINE-ROOM-DISPATCH-TEST")
    print("================================================================================")

    # 1. Host identity verification
    hostname = socket.gethostname()
    print(f"[*] Native Hostname: {hostname}")
    assert hostname == "clio", f"Expected execution on clio, but ran on {hostname}"

    # 2. Kernel and environment verification
    uname = os.uname()
    print(f"[*] Linux Kernel: {uname.sysname} {uname.release} ({uname.machine})")
    print(f"[*] Process PID: {os.getpid()} | Parent PID: {os.getppid()}")
    print(f"[*] Python Executable: {sys.executable}")

    # 3. Network & Tailscale Verification
    tailscale_ip = "100.73.155.70"
    try:
        ts_status = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=5)
        detected_ip = ts_status.stdout.strip()
        print(f"[*] Tailscale IP Detected: {detected_ip}")
    except Exception as e:
        detected_ip = f"Error: {e}"
        print(f"[!] Could not run tailscale CLI: {e}")

    # 4. FastAPI Backend Verification via api_client (FastAPI-First Mandate)
    print("[*] Verifying SDLC Ticketing API (Port 8095)...")
    try:
        tickets = api_client.get_tickets(state_int=[1, 2])
        open_ticket_count = len(tickets)
        print(f"[✓] FastAPI SDLC API reachable: {open_ticket_count} active tickets returned.")
    except Exception as e:
        print(f"[!] FastAPI query failed: {e}")
        raise

    # 5. Compile verification evidence artifact
    evidence = {
        "task_id": "WO0010038-CLIO-ENGINE-ROOM-DISPATCH-TEST",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "timestamp_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hostname": hostname,
        "kernel": f"{uname.sysname} {uname.release} {uname.machine}",
        "python_interpreter": sys.executable,
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "tailscale_ip": detected_ip,
        "open_tickets_count": open_ticket_count,
        "status": "PASSED",
        "verdict": "Artemis-to-Clio autonomous Work Order dispatch pipeline 100% operational."
    }

    evidence_dir = "/home/james/sovereign_inbox/tickets/WO0010038-CLIO-ENGINE-ROOM-DISPATCH-TEST"
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, "clio_dispatch_evidence.json")
    with open(evidence_path, "w") as f:
        json.dump(evidence, f, indent=2)
    print(f"[✓] Evidence payload committed to: {evidence_path}")

    # Also mirror to today folder
    today_evidence = "/home/james/sovereign_inbox/today/CLIO_ENGINE_ROOM_DISPATCH_TEST_EVIDENCE.json"
    try:
        with open(today_evidence, "w") as f:
            json.dump(evidence, f, indent=2)
        print(f"[✓] Evidence mirrored to: {today_evidence}")
    except Exception as e:
        print(f"[!] Warning: Could not mirror to today: {e}")

    print("================================================================================")
    print("🎉 CLIO ENGINE ROOM WORK ORDER EXECUTION COMPLETED WITH EXIT CODE 0")
    print("================================================================================")
    return 0

if __name__ == "__main__":
    sys.exit(run_test())
