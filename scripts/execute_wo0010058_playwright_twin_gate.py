#!/usr/bin/env python3
"""
Sovereign OS — Rule IV.2.b Playwright Visual Twin Gate Test Suite
Ticket: WO0010058-SDLC-PLAYWRIGHT-VISUAL-TWIN-RESOLUT
Path: /home/james/stacklabs/scripts/execute_wo0010058_playwright_twin_gate.py

Validates:
1. HTTP 422 Rejection on UI ticket resolution without verified Pegasus visual twin (Rule IV.2.b).
2. HTTP 422 Rejection on batch resolution of UI tickets without visual twin.
3. HTTP 200 Bypass for non-UI tickets (e.g. backend/infra).
4. HTTP 200 Success for UI ticket once verified visual twin is attached.
5. Reconciliation and resolution of WO0010058.
"""

import sys
import os
import json
import httpx
from datetime import datetime

sys.path.insert(0, "/home/james/stacklabs")
from scripts.core import api_client

PORTAL_API = "http://127.0.0.1:8095"

def run_tests():
    print("================================================================================")
    print("🚀 SOVEREIGN OS: RULE IV.2.b PEGASUS PLAYWRIGHT VISUAL TWIN GATE VERIFICATION")
    print("================================================================================")

    # 1. Create temporary UI test ticket
    print("\n[Phase 1] Staging temporary UI ticket...")
    res = httpx.post(f"{PORTAL_API}/api/tickets", json={
        "ticket_type": "Story",
        "title": "Test FanStack Dynamic Playcall View & Widget",
        "description": "Testing UI ticket resolution hard-gate enforcement.",
        "affected_ci": "15_FanStack",
        "assigned_to": "antigravity",
        "priority": "P2"
    }, timeout=10.0)
    assert res.status_code == 200, f"Failed to create UI test ticket: {res.text}"
    ui_ticket = res.json()
    ui_id = ui_ticket["id"]
    print(f"✔ Created UI test ticket: {ui_id}")

    # 2. Test 1: Attempt resolution WITHOUT visual twin -> MUST return HTTP 422
    print("\n[Phase 2] Test 1: Attempting to resolve UI ticket without visual twin...")
    res = httpx.put(f"{PORTAL_API}/api/tickets/{ui_id}", json={
        "status": "RESOLVED",
        "work_notes": "Attempting unauthorized resolution without visual twin."
    }, timeout=10.0)
    
    print(f"Status Code: {res.status_code}")
    print(f"Response Body: {res.text}")
    assert res.status_code == 422, f"Expected 422 Unprocessable Entity, got {res.status_code}"
    err = res.json()
    assert err.get("code") == "RULE_IV_2_B", f"Expected error code RULE_IV_2_B, got {err.get('code')}"
    assert "Pegasus Playwright" in err.get("detail", ""), "Detail must cite Pegasus Playwright"
    print("✔ Test 1 PASSED: UI ticket resolution blocked with HTTP 422 (RULE_IV_2_B).")

    # Test 1b: Attempt batch resolution WITHOUT visual twin -> MUST return HTTP 422
    print("\n[Phase 2b] Test 1b: Attempting batch resolution of UI ticket without visual twin...")
    res = httpx.post(f"{PORTAL_API}/api/tickets/batch_update", json={
        "action": "RESOLVE",
        "ticket_ids": [ui_id],
        "work_notes": "Batch resolve attempt without visual twin."
    }, timeout=10.0)
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 422, f"Expected 422 for batch update, got {res.status_code}"
    err = res.json()
    assert err.get("code") == "RULE_IV_2_B", f"Expected error code RULE_IV_2_B, got {err.get('code')}"
    print("✔ Test 1b PASSED: Batch resolution blocked with HTTP 422 (RULE_IV_2_B).")

    # 3. Test 2: Non-UI ticket resolution -> MUST succeed with HTTP 200
    print("\n[Phase 3] Test 2: Staging non-UI backend ticket...")
    res = httpx.post(f"{PORTAL_API}/api/tickets", json={
        "ticket_type": "ENHANCEMENT",
        "title": "[NON-UI] Core Daemon Connection Pool Tuning",
        "description": "Pure backend database pooling tuning.",
        "affected_ci": "sovereign_knot_core",
        "assigned_to": "antigravity",
        "priority": "P3"
    }, timeout=10.0)
    assert res.status_code == 200, f"Failed to create non-UI ticket: {res.text}"
    non_ui_id = res.json()["id"]
    print(f"✔ Created non-UI ticket: {non_ui_id}")

    print("Attempting to resolve non-UI ticket...")
    res = httpx.put(f"{PORTAL_API}/api/tickets/{non_ui_id}", json={
        "status": "RESOLVED",
        "work_notes": "Backend tuning verified."
    }, timeout=10.0)
    assert res.status_code == 200, f"Expected 200 for non-UI ticket, got {res.status_code}: {res.text}"
    print("✔ Test 2 PASSED: Non-UI ticket successfully resolved without visual twin requirement.")

    # 4. Test 3: Attach verified visual twin -> UI Ticket resolution MUST succeed with HTTP 200
    print("\n[Phase 4] Test 3: Attaching verified Pegasus Playwright visual twin to UI ticket...")
    # Create mock screenshot file
    sample_img_path = "/tmp/pegasus_visual_twin_test_uat.png"
    # Create simple PNG header bytes
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    with open(sample_img_path, "wb") as f:
        f.write(png_bytes)

    upload_res = api_client.upload_ticket_attachment(ui_id, sample_img_path, filename="pegasus_visual_twin_test_uat.png")
    print(f"✔ Uploaded twin attachment: {upload_res}")

    print("Attempting to resolve UI ticket WITH verified visual twin attached...")
    res = httpx.put(f"{PORTAL_API}/api/tickets/{ui_id}", json={
        "status": "RESOLVED",
        "work_notes": "Resolved with verified Pegasus Playwright live visual twin."
    }, timeout=10.0)
    assert res.status_code == 200, f"Expected 200 after visual twin attachment, got {res.status_code}: {res.text}"
    print("✔ Test 3 PASSED: UI ticket resolution permitted following visual twin attachment.")

    # Verify state is 4 (RESOLVED)
    ticket_data = api_client.get_ticket(ui_id)
    assert ticket_data.get("state_int") == 4 or ticket_data.get("status") in ("DONE", "RESOLVED"), f"Ticket state not resolved: {ticket_data}"
    print("✔ Verified ticket state is RESOLVED (4).")

    # Clean up test tickets
    print("\n[Phase 5] Cleaning up test tickets...")
    httpx.delete(f"{PORTAL_API}/api/tickets/{ui_id}", timeout=5.0)
    httpx.delete(f"{PORTAL_API}/api/tickets/{non_ui_id}", timeout=5.0)
    if os.path.exists(sample_img_path):
        os.remove(sample_img_path)
    print("✔ Test tickets cleaned up.")

    print("\n================================================================================")
    print("🎉 ALL 4 TEST SCENARIOS PASSED: RULE IV.2.b HARD-GATE FULLY VERIFIED")
    print("================================================================================")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
