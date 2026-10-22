#!/usr/bin/env python3
"""
scripts/verify_wo0011038_vfs_engine.py
Automated Verification Harness for Hardened WO0011038
Target Silicon: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
Invariants: 0, 8, 15, 32, 35, 50
"""

import os
import sys
import shutil
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = "/home/james/stacklabs"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.blueprints.vfs_recursive_router import (
    router,
    DEFAULT_VFS_ROOT,
    RUNBOOKS_DIR,
    OUTBOX_RECEIPTS_DIR,
    RUNBOOK_REGISTRY
)

app = FastAPI()
app.include_router(router)
client = TestClient(app)

TEST_DIR = DEFAULT_VFS_ROOT / "test_estate_suite"
AUTH_HEADERS = {"Authorization": "Bearer stacklabs_metal_pawel_2026"}


def setup_test_suite():
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)

    ranch_dir = TEST_DIR / "montana_ranch"
    ranch_dir.mkdir(parents=True, exist_ok=True)

    # Seed regular leaves
    (ranch_dir / "gate_cam.stream").write_text("http://192.168.1.189:8080/live.m3u8")
    (ranch_dir / "solar_volts.tail").write_text("12.4V\n12.5V\n12.6V\n")
    (ranch_dir / "ranch_notes.md").write_text("# Montana Ranch Notes\n500 acres verified.")
    (ranch_dir / "pump.action").write_text('{"action_id": "system_pump_cycle"}')

    # Seed restricted vault
    vault_dir = TEST_DIR / "_vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    (vault_dir / "private_trust.md").write_text("Secret Trust Ledger")

    # Seed broken symlink
    broken_link = ranch_dir / "dangling_sensor.tail"
    if broken_link.exists() or broken_link.is_symlink():
        broken_link.unlink()
    os.symlink("/nonexistent/file/path", broken_link)

    # Seed runbook script in RUNBOOKS_DIR if not present
    pump_script = RUNBOOKS_DIR / "system_pump_cycle.sh"
    if not pump_script.exists():
        pump_script.write_text("#!/bin/bash\necho 'PUMP_CYCLED_OK'\nexit 0\n")
    pump_script.chmod(0o755)


def teardown_test_suite():
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)


def run_tests():
    setup_test_suite()
    try:
        print("[1/8] Verifying basic container & leaf browsing...")
        res = client.get("/api/vfs/recursive/browse?path=test_estate_suite", headers=AUTH_HEADERS)
        if res.status_code != 200:
            raise AssertionError(f"Browse failed with code {res.status_code}: {res.text}")
        data = res.json()
        container_names = [c["name"] for c in data["containers"]]
        if "montana_ranch" not in container_names:
            raise AssertionError("montana_ranch container missing")

        print("[2/8] Verifying path traversal attack rejection (prefix & escaping)...")
        res_trav1 = client.get("/api/vfs/recursive/browse?path=../../etc", headers=AUTH_HEADERS)
        if res_trav1.status_code != 403:
            raise AssertionError(f"Expected 403 on path traversal, got {res_trav1.status_code}")

        res_trav2 = client.get("/api/vfs/recursive/browse?path=../vfs_evil", headers=AUTH_HEADERS)
        if res_trav2.status_code != 403:
            raise AssertionError(f"Expected 403 on prefix collision, got {res_trav2.status_code}")

        print("[3/8] Verifying dangling symlink resilience...")
        res_child = client.get("/api/vfs/recursive/browse?path=test_estate_suite/montana_ranch", headers=AUTH_HEADERS)
        if res_child.status_code != 200:
            raise AssertionError(f"Child browse failed: {res_child.text}")
        child_data = res_child.json()
        dangling_leaves = [l for l in child_data["leaves"] if l["leaf_type"] == "dangling"]
        if not dangling_leaves:
            raise AssertionError("Broken symlink was not classified as dangling")

        print("[4/8] Verifying guest boundary on restricted vault (404 anti-enumeration)...")
        res_guest_vault = client.get("/api/vfs/recursive/browse?path=test_estate_suite/_vault")
        if res_guest_vault.status_code != 404:
            raise AssertionError(f"Expected 404 for unauthenticated vault browse, got {res_guest_vault.status_code}")

        res_auth_vault = client.get("/api/vfs/recursive/browse?path=test_estate_suite/_vault", headers=AUTH_HEADERS)
        if res_auth_vault.status_code != 200:
            raise AssertionError(f"Expected 200 for authenticated vault browse, got {res_auth_vault.status_code}")

        print("[5/8] Verifying reverse-seek log tail reading...")
        res_tail = client.get("/api/vfs/recursive/read?path=test_estate_suite/montana_ranch/solar_volts.tail&tail_lines=2", headers=AUTH_HEADERS)
        if res_tail.status_code != 200:
            raise AssertionError(f"Tail read failed: {res_tail.text}")
        tail_data = res_tail.json()
        if "12.6V" not in tail_data["content"]:
            raise AssertionError("Tail content missing latest line")

        print("[6/8] Verifying unauthenticated action execution rejection (403)...")
        res_unauth_action = client.post("/api/vfs/recursive/execute_action", json={
            "action_id": "system_pump_cycle",
            "parameters": {}
        })
        if res_unauth_action.status_code != 403:
            raise AssertionError(f"Expected 403 on unauthenticated action, got {res_unauth_action.status_code}")

        print("[7/8] Verifying unapproved action rejection (RCE prevention)...")
        res_bad_action = client.post("/api/vfs/recursive/execute_action", headers=AUTH_HEADERS, json={
            "action_id": "unapproved_arbitrary_script",
            "parameters": {}
        })
        if res_bad_action.status_code != 403:
            raise AssertionError(f"Expected 403 on unapproved action ID, got {res_bad_action.status_code}")

        print("[8/8] Verifying pre-approved runbook execution & outbox receipt creation...")
        res_action = client.post("/api/vfs/recursive/execute_action", headers=AUTH_HEADERS, json={
            "action_id": "system_pump_cycle",
            "parameters": {"zone": "north"}
        })
        if res_action.status_code != 200:
            raise AssertionError(f"Action execution failed: {res_action.text}")
        action_data = res_action.json()
        if action_data["returncode"] != 0 or "PUMP_CYCLED_OK" not in action_data["stdout"]:
            raise AssertionError(f"Unexpected action output: {action_data}")

        receipt_id = action_data["receipt_id"]
        receipt_file = OUTBOX_RECEIPTS_DIR / f"{receipt_id}.json"
        if not receipt_file.exists():
            raise AssertionError(f"Outbox receipt file {receipt_file} was not written to NVMe")

        print("✅ ALL 8 HARDENED VERIFICATION TESTS PASSED CLEANLY ON METAL.")
    finally:
        teardown_test_suite()


if __name__ == "__main__":
    run_tests()
