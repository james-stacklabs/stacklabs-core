#!/usr/bin/env python3
"""
Test Suite: Autonomous JIT Dispatcher Execution Loop & Spin-Loop Elimination
Path: /home/james/stacklabs/scripts/test_autonomous_dispatcher_loop.py
Initiative: DFCT0010002-AUTONOMOUS-DISPATCHER-EXECUTION-LOOP
"""

import sys
import os
import time
import json
import sqlite3
from pathlib import Path

sys.path.insert(0, '/home/james/stacklabs')

from scripts.core import api_client
from scripts.antigravity_dispatcher import process_approved_tickets

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def setup_test_work_orders():
    # 1. Create executable test script
    test_script_path = "/home/james/stacklabs/scripts/execute_test_wo_executable_01.py"
    with open(test_script_path, "w") as f:
        f.write("#!/usr/bin/env python3\nprint('TEST EXECUTION SUCCESSFUL!')\n")
    os.chmod(test_script_path, 0o755)

    # 2. Create Executable Work Order via FastAPI REST Client
    api_client.create_ticket(
        title="Test Executable Work Order",
        ticket_type="Story",
        description="Executable test plan",
        priority="P2",
        status="OPEN",
        assigned_to="james",
        affected_ci="antigravity_dispatcher"
    )
    api_client.create_approval(
        task_id="TEST-WO-EXECUTABLE-01",
        title="Test Executable Work Order",
        plan_markdown="Executable test plan",
        state="Approved",
        auth_level="omega=1",
        sys_id="appr_test_exec_01"
    )

    # 3. Create Unmapped Work Order via FastAPI REST Client
    api_client.create_ticket(
        title="Test Unmapped Work Order",
        ticket_type="Story",
        description="Unmapped UI design plan requiring Antigravity interactive implementation",
        priority="P2",
        status="OPEN",
        assigned_to="james",
        affected_ci="antigravity_dispatcher"
    )
    api_client.create_approval(
        task_id="TEST-WO-UNMAPPED-02",
        title="Test Unmapped Work Order",
        plan_markdown="Unmapped UI design plan requiring Antigravity interactive implementation",
        state="Approved",
        auth_level="omega=1",
        sys_id="appr_test_unmapped_02"
    )

def test_dispatcher_execution():
    print("\n=======================================================")
    print("TEST 1: Autonomous Dispatcher Execution of Script Hook")
    print("=======================================================")
    
    setup_test_work_orders()
    
    # Run dispatcher pass 1
    print("[PASS 1] Running dispatcher process pass...")
    process_approved_tickets()
    
    # Verify Executable Work Order was transitioned to Executed
    appr1 = api_client.get_approvals(task_id="TEST-WO-EXECUTABLE-01")
    print(f"Approval Status for TEST-WO-EXECUTABLE-01: {appr1[0]['state']}")
    assert appr1[0]['state'] == "Executed", "Executable work order must be transitioned to Executed"
    print("✓ Passed: Executable work order executed and marked 'Executed' (omega=1).")

    print("\n=======================================================")
    print("TEST 2: Elimination of Spin-Loop on Unmapped Work Order")
    print("=======================================================")
    
    # Verify Unmapped Work Order was transitioned to Pending Implementation (NOT Approved)
    appr2 = api_client.get_approvals(task_id="TEST-WO-UNMAPPED-02")
    print(f"Approval Status for TEST-WO-UNMAPPED-02 after Pass 1: {appr2[0]['state']}")
    assert appr2[0]['state'] == "Pending Implementation", "Unmapped work order must be set to 'Pending Implementation'"
    print("✓ Passed: Unmapped work order transitioned to 'Pending Implementation' (exit 99 handled).")

    # Run dispatcher pass 2 (Must find ZERO approved work orders and do nothing)
    print("\n[PASS 2] Running second dispatcher pass to verify no spin-loop...")
    process_approved_tickets()
    
    # Check that appr2 state remained Pending Implementation
    appr2_after = api_client.get_approvals(task_id="TEST-WO-UNMAPPED-02")
    assert appr2_after[0]['state'] == "Pending Implementation", "State must remain Pending Implementation without looping"
    print("✓ Passed: Second pass completed with 0 re-pickups. Spin loop is permanently eradicated!")

def cleanup():
    try:
        api_client.update_approval("appr_test_exec_01", state="Dismissed")
        api_client.update_approval("appr_test_unmapped_02", state="Dismissed")
    except Exception:
        pass
    
    test_script_path = "/home/james/stacklabs/scripts/execute_test_wo_executable_01.py"
    if os.path.exists(test_script_path):
        os.remove(test_script_path)

if __name__ == "__main__":
    try:
        test_dispatcher_execution()
        print("\n=======================================================")
        print("🎉 ALL AUTONOMOUS DISPATCHER TESTS PASSED CLEANLY!")
        print("=======================================================\n")
    finally:
        cleanup()
