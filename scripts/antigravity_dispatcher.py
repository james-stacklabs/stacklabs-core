#!/usr/bin/env python3
"""
Sovereign OS: Antigravity Autonomous JIT Execution Dispatcher Daemon
Path: /home/james/stacklabs/scripts/antigravity_dispatcher.py
Initiative: DFCT0010002-AUTONOMOUS-DISPATCHER-EXECUTION-LOOP

Governed by WO-2026-ANTIGRAVITY-JIT-DISPATCHER-024 & DFCT0010002.
Monitors Port 8095 FastAPI Approval Queue for approved Work Orders (state='Approved', auth_level='omega=1'),
file locks execution passes, transitions ticket states (OPEN -> WIP -> RESOLVED / PENDING_IMPLEMENTATION),
executes associated automated scripts / pipelines, and eliminates the exit-99 spin loop defect.
"""

import os
import sys
import time
import fcntl
import json
import re
import hashlib
import subprocess
import traceback
from datetime import datetime, timezone

SOVEREIGN_HOME = "/home/james/stacklabs"
sys.path.insert(0, SOVEREIGN_HOME)

from scripts.core import api_client

LOG_PATH = f"{SOVEREIGN_HOME}/logs/antigravity_dispatcher.log"
LOCK_FILE = "/tmp/antigravity_exec.lock"
LEDGER_PATH = f"{SOVEREIGN_HOME}/logs/sovereign_fin_ledger.jsonl"

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)

def log_msg(level: str, text: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level.upper()}] {text}"
    print(formatted, flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(formatted + "\n")
    except Exception as e:
        print(f"Failed to append to log file: {e}", flush=True)

def record_ledger_entry(task_id: str, omega_auth: str, status: str):
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        raw_token = f"{task_id}:{omega_auth}:{timestamp}:{status}"
        sha_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        entry = {
            "timestamp": timestamp,
            "task_id": task_id,
            "auth_level": omega_auth,
            "status": status,
            "sha256": sha_hash
        }
        with open(LEDGER_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
        log_msg("info", f"Audit ledger entry recorded for {task_id} (SHA256: {sha_hash[:12]}...)")
    except Exception as e:
        log_msg("error", f"Failed to record ledger entry: {e}")

def find_script_in_text(text: str):
    if not text:
        return None
    matches = re.findall(r"(/[\w/-]+\.py|scripts/[\w/-]+\.py)", text)
    for m in matches:
        full_p = m if m.startswith("/") else os.path.join(SOVEREIGN_HOME, m)
        if os.path.exists(full_p):
            return full_p
    return None

def process_approved_tickets():
    try:
        # FastAPI-First query for approved work orders awaiting execution
        approved_requests = api_client.get_approvals(state="Approved", auth_level="omega=1")
        if not approved_requests:
            # Also check for wildcard omega
            all_approved = api_client.get_approvals(state="Approved")
            approved_requests = [r for r in all_approved if "omega" in str(r.get("auth_level", "")).lower()]
    except Exception as e:
        log_msg("warning", f"Could not fetch approved requests via API: {e}")
        return

    if not approved_requests:
        return

    for req in approved_requests:
        sys_id = req.get("sys_id") or req.get("id")
        task_id = req.get("task_id") or sys_id
        title = req.get("title", "Untitled Work Order")
        auth_level = req.get("auth_level", "omega=1")
        plan_markdown = req.get("plan_markdown", "")

        log_msg("info", f"⚡ [PICKUP] Found approved work order: {task_id} - '{title}'")

        # Transition approval state to 'Executing' via REST API
        try:
            api_client.update_approval(sys_id, state="Executing")
            api_client.update_ticket(task_id, {
                "state_int": 2,
                "status": "IN_PROGRESS",
                "work_notes": "Antigravity Dispatcher picked up ticket for autonomous execution."
            })
            log_msg("info", f"State transitioned to IN_PROGRESS for {task_id}.")
        except Exception as e:
            log_msg("error", f"Failed to transition state for {task_id}: {e}")

        clean_task_name = task_id.lower().replace("-", "_")
        script_candidates = [
            f"{SOVEREIGN_HOME}/scripts/execute_{clean_task_name}.py",
            f"{SOVEREIGN_HOME}/scripts/execute_{task_id.lower()}.py"
        ]

        # Also check if script referenced directly in plan markdown
        plan_script = find_script_in_text(plan_markdown)
        if plan_script and os.path.exists(plan_script):
            script_candidates.insert(0, plan_script)

        exec_script = None
        for cand in script_candidates:
            if cand and os.path.exists(cand):
                exec_script = cand
                break

        exit_code = 0
        error_output = ""

        if exec_script:
            log_msg("info", f"Executing target script hook: {exec_script}")
            cmd = [f"{SOVEREIGN_HOME}/.venv/bin/python3", exec_script]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                log_msg("info", f"Script STDOUT:\n{res.stdout}")
                if res.returncode != 0:
                    exit_code = res.returncode
                    error_output = res.stderr
                    log_msg("error", f"Script STDERR:\n{res.stderr}")
            except Exception as ex:
                exit_code = 1
                error_output = str(ex)
                log_msg("error", f"Subprocess execution error: {ex}")
        else:
            log_msg("info", f"No static script hook found for {task_id}. Checking headless worker...")
            worker_script = f"{SOVEREIGN_HOME}/scripts/sovereign_headless_worker.py"
            if os.path.exists(worker_script):
                cmd = [f"{SOVEREIGN_HOME}/.venv/bin/python3", worker_script, task_id, title, plan_markdown]
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                    log_msg("info", f"Headless Worker STDOUT:\n{res.stdout}")
                    exit_code = res.returncode
                    if exit_code != 0:
                        error_output = res.stderr
                except Exception as ex:
                    exit_code = 1
                    error_output = str(ex)
            else:
                exit_code = 99
                error_output = "No headless worker engine available."

        # State Resolution & Spin-Loop Elimination (DFCT0010002)
        if exit_code == 0:
            try:
                api_client.update_approval(sys_id, state="Executed", auth_level="omega=1")
                api_client.update_ticket(task_id, {
                    "state_int": 5,
                    "status": "RESOLVED",
                    "work_notes": "24/7 Autonomous JIT execution completed successfully."
                })
            except Exception as e:
                log_msg("error", f"Failed to mark resolved via API: {e}")
            log_msg("info", f"✔ [RESOLVED] Task {task_id} completed successfully with exit code 0.")
            record_ledger_entry(task_id, auth_level, "RESOLVED")
        elif exit_code == 99:
            # DFCT0010002 FIX: Mark state as 'Pending Implementation' (NEVER reset to 'Approved')
            try:
                api_client.update_approval(sys_id, state="Pending Implementation")
                api_client.update_ticket(task_id, {
                    "state_int": 2,
                    "status": "IN_PROGRESS",
                    "work_notes": "Approved by Pilot (omega=1). Plan staged in sovereign_inbox for interactive Antigravity implementation."
                })
            except Exception as e:
                log_msg("error", f"Failed to stage ticket via API: {e}")
            log_msg("info", f"⚡ [STAGED] Task {task_id} staged for interactive Antigravity implementation (exit 99 - loop terminated).")
            record_ledger_entry(task_id, auth_level, "PENDING_IMPLEMENTATION")
        else:
            try:
                api_client.update_approval(sys_id, state="Failed")
                api_client.update_ticket(task_id, {
                    "state_int": 1,
                    "status": "OPEN",
                    "work_notes": f"Autonomous execution failed (exit {exit_code}): {error_output[:500]}"
                })
            except Exception as e:
                log_msg("error", f"Failed to mark failed via API: {e}")
            log_msg("error", f"❌ [FAILED] Task {task_id} failed with exit code {exit_code}.")
            record_ledger_entry(task_id, auth_level, "FAILED")

def main_loop():
    log_msg("info", "=========================================================")
    log_msg("info", "Sovereign OS Antigravity JIT Execution Dispatcher Daemon starting...")
    log_msg("info", "Operating Mode: FastAPI-First REST Client (Port 8095)")

    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        log_msg("warning", "Another instance of antigravity_dispatcher.py is running. Exiting.")
        sys.exit(0)

    log_msg("info", "Exclusive lock acquired. Polling loop active (interval: 3s).")

    try:
        while True:
            try:
                process_approved_tickets()
            except Exception as e:
                log_msg("error", f"Unhandled exception in dispatcher loop: {e}")
                traceback.print_exc()
            time.sleep(3)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

if __name__ == "__main__":
    main_loop()
