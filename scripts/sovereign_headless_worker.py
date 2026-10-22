#!/usr/bin/env python3
"""
Sovereign OS: 24/7 Autonomous Headless AI Worker Engine
Path: /home/james/stacklabs/scripts/sovereign_headless_worker.py
Initiative: DFCT0010002-AUTONOMOUS-DISPATCHER-EXECUTION-LOOP

Autonomous backend agent that executes approved JIT work orders 24/7 headlessly.
Generates canonical implementation plans, executes bound script hooks, writes SDLC walkthroughs,
and safely stages unmapped interactive tasks without spin-looping.
"""

import os
import sys
import json
import time
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path

SOVEREIGN_HOME = "/home/james/stacklabs"
sys.path.insert(0, SOVEREIGN_HOME)

INBOX_PATH = "/home/james/sovereign_inbox"

def log(text: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [HEADLESS_WORKER] {text}", flush=True)

def find_script_in_markdown(text: str):
    if not text:
        return None
    matches = re.findall(r"(/home/james/stacklabs/scripts/[\w/-]+\.py|scripts/[\w/-]+\.py)", text)
    for m in matches:
        full_p = m if m.startswith("/") else os.path.join(SOVEREIGN_HOME, m)
        if os.path.exists(full_p):
            return full_p
    return None

def execute_autonomous_story(task_id: str, title: str, plan_markdown: str) -> int:
    log(f"⚡ Beginning 24/7 Autonomous Execution for: {task_id} ('{title}')")
    
    # 1. Ensure canonical directories and ticket package directory exist
    os.makedirs(f"{INBOX_PATH}/implementation_plans", exist_ok=True)
    os.makedirs(f"{INBOX_PATH}/walkthroughs", exist_ok=True)
    ticket_pkg_dir = f"{INBOX_PATH}/tickets/{task_id}"
    os.makedirs(ticket_pkg_dir, exist_ok=True)
    
    plan_file = f"{INBOX_PATH}/implementation_plans/implementation_plan_{task_id}.md"
    pkg_plan_file = f"{ticket_pkg_dir}/implementation_plan.md"
    walkthrough_file = f"{INBOX_PATH}/walkthroughs/walkthrough_{task_id}.md"
    pkg_walkthrough_file = f"{ticket_pkg_dir}/walkthrough.md"
    
    iso_now = datetime.now(timezone.utc).isoformat()
    plan_content = f"""# Implementation Plan — {task_id}

**Title:** {title}  
**Execution Mode:** 24/7 Autonomous Headless Worker (Node Clio)  
**Timestamp:** `{iso_now}`  

---

## 1. Technical Specification & Work Order Plan

{plan_markdown if plan_markdown.strip() else 'Autonomous Work Order staged for execution.'}
"""
    # Write canonical implementation plans
    with open(plan_file, "w", encoding="utf-8") as f:
        f.write(plan_content)
    with open(pkg_plan_file, "w", encoding="utf-8") as f:
        f.write(plan_content)
    log(f"✔ Canonical implementation plan generated at {plan_file} and {pkg_plan_file}")
    
    # 2. Check for domain-specific python script hook or scripts mentioned in plan
    clean_task_name = task_id.lower().replace("-", "_")
    script_candidates = [
        f"{SOVEREIGN_HOME}/scripts/execute_{clean_task_name}.py",
        f"{SOVEREIGN_HOME}/scripts/execute_{task_id.lower()}.py"
    ]
    
    plan_script = find_script_in_markdown(plan_markdown)
    if plan_script and os.path.exists(plan_script):
        script_candidates.insert(0, plan_script)
        
    exec_script = None
    for cand in script_candidates:
        if cand and os.path.exists(cand):
            exec_script = cand
            break
            
    exec_success = False
    exec_notes = []
    
    if exec_script:
        log(f"Executing localized task script hook: {exec_script}")
        try:
            res = subprocess.run([f"{SOVEREIGN_HOME}/.venv/bin/python3", exec_script], capture_output=True, text=True, timeout=600)
            if res.returncode == 0:
                log(f"✔ Task script hook {exec_script} succeeded.")
                exec_success = True
                exec_notes.append(f"Executed script hook `{exec_script}` successfully.")
            else:
                log(f"❌ Task script hook {exec_script} failed: {res.stderr}")
                exec_notes.append(f"Script failure in `{exec_script}`: {res.stderr[:300]}")
        except Exception as ex:
            log(f"❌ Subprocess execution error: {ex}")
            exec_notes.append(f"Execution exception: {ex}")
    else:
        # No automated execution script hook found.
        # Stage the plan for interactive Antigravity implementation without spin-looping
        log(f"⚡ No automated execution script hook found for {task_id}.")
        log(f"✔ Canonical plan staged. Returning exit code 99 to signal interactive staging.")
        return 99

    if not exec_success:
        return 1

    # 3. Generate Canonical Walkthrough (Compliant with Rule IV.7 & IV.4)
    walkthrough_content = f"""# 🚀 SDLC TICKET WALKTHROUGH
## {task_id}: {title}
**Ticket ID:** `{task_id}`  
**Status:** **RESOLVED (`state = 5`)**  
**Execution Node:** `clio`  
**Execution Engine:** Sovereign Autonomous Headless AI Worker  
**Authorization:** $\\Omega=1$ (Signed via JIT Mobile Approval Gateway)  
**Timestamp:** `{iso_now}`  

---

## 📖 1. User Operations & Quick Start Guide

### Overview of Autonomous Delivery
This deliverable was executed autonomously by the Sovereign JIT Dispatcher following Omega-1 Pilot approval.

### Operational Verification
1. To inspect execution artifacts, review the ticket package directory:
   `tickets/{task_id}/`
2. Audit ledger hash recorded in `/home/james/stacklabs/logs/sovereign_fin_ledger.jsonl`.
3. To test the deliverable, run the bound verification script or check the corresponding service port.

---

## ⚙️ 2. Autonomous Execution Summary

- **Script Hook Executed:** `{exec_script}`
- **Execution Status:** **SUCCESS (Exit Code 0)**
- **Technical Notes:** {"; ".join(exec_notes)}

---

## 📦 3. SDLC Reconciliation
- Ticket `{task_id}` updated to `RESOLVED` in `sovereign_tickets`.
- Matching approval record in `sys_approval_queue` reconciled to `Executed` (`omega=1`).
"""
    with open(walkthrough_file, "w", encoding="utf-8") as f:
        f.write(walkthrough_content)
    with open(pkg_walkthrough_file, "w", encoding="utf-8") as f:
        f.write(walkthrough_content)
    log(f"✔ Canonical walkthrough generated at {walkthrough_file}")
    
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: sovereign_headless_worker.py <task_id> <title> [plan_markdown]")
        sys.exit(1)
    t_id = sys.argv[1]
    t_title = sys.argv[2]
    t_plan = sys.argv[3] if len(sys.argv) > 3 else ""
    code = execute_autonomous_story(t_id, t_title, t_plan)
    sys.exit(code)
