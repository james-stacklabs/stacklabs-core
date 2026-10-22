#!/usr/bin/env python3
"""
Verification Script for WO0011063:
Rebuild Workstation Command Cockpit on Port 8088 with KISS & LITE Digital Twin Architecture
"""

import sys
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
COCKPIT_TEMPLATE = REPO_ROOT / "scripts/templates/cockpit.html"
BASE_URL = "http://127.0.0.1:8088"

def log_pass(msg):
    print(f"[\033[92mPASS\033[0m] {msg}")

def log_fail(msg):
    print(f"[\033[91mFAIL\033[0m] {msg}")
    sys.exit(1)

def test_1_line_count():
    if not COCKPIT_TEMPLATE.exists():
        log_fail(f"Template not found at {COCKPIT_TEMPLATE}")
    lines = COCKPIT_TEMPLATE.read_text(encoding="utf-8").splitlines()
    count = len(lines)
    if count < 600:
        log_pass(f"Test 1: cockpit.html line count is {count} (< 600 lines)")
    else:
        log_fail(f"Test 1: cockpit.html line count is {count} (exceeds 600 lines)")

def test_2_no_neon_or_filler():
    content = COCKPIT_TEMPLATE.read_text(encoding="utf-8")
    banned_tokens = [
        "border-cyan-500",
        "border-amber-500",
        "border-green-500",
        "Metal Cockpit",
        "CLIO 35W"
    ]
    found = [t for t in banned_tokens if t in content]
    if not found:
        log_pass("Test 2: Zero neon classes or filler badges found in cockpit.html")
    else:
        log_fail(f"Test 2: Found banned tokens in cockpit.html: {found}")

def test_3_get_cockpit():
    url = f"{BASE_URL}/cockpit"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            body = resp.read().decode("utf-8")
            if resp.status == 200 and "STACKLABS" in body and "Metal Forge" in body:
                log_pass(f"Test 3: GET {url} -> 200 OK (Clean DOM served)")
            else:
                log_fail(f"Test 3: Unexpected response from {url} status={resp.status}")
    except Exception as e:
        log_fail(f"Test 3: GET {url} failed: {e}")

def test_4_get_queue():
    url = f"{BASE_URL}/api/cockpit/queue"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                assert "incoming_count" in data, "incoming_count missing"
                assert "incoming_tickets" in data, "incoming_tickets missing"
                assert "recent_archive" in data, "recent_archive missing"
                log_pass(f"Test 4: GET {url} -> 200 OK (Valid queue telemetry schema)")
            else:
                log_fail(f"Test 4: GET {url} returned status {resp.status}")
    except Exception as e:
        log_fail(f"Test 4: GET {url} failed: {e}")

def test_5_post_quickdrop():
    url = f"{BASE_URL}/api/cockpit/quickdrop"
    payload = json.dumps({"text": "WO0011063 automated verification receipt"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if resp.status == 200 and data.get("status") == "success":
                scratch_file = REPO_ROOT / "pilot_drops/pilot_scratch_pad.md"
                assert scratch_file.exists(), f"Scratchpad not found at {scratch_file}"
                scratch_content = scratch_file.read_text(encoding="utf-8")
                assert "WO0011063 automated verification receipt" in scratch_content, "Receipt text not found in scratchpad"
                log_pass(f"Test 5: POST {url} -> 200 OK & confirmed in pilot_scratch_pad.md")
            else:
                log_fail(f"Test 5: Unexpected response: {data}")
    except Exception as e:
        log_fail(f"Test 5: POST {url} failed: {e}")

def test_6_voice_and_file_drops():
    # Voice Drop test
    url_voice = f"{BASE_URL}/api/cockpit/voice_drop"
    req_voice = urllib.request.Request(url_voice, data=b"RIFF\x24\x00\x00\x00WAVEfmt ", method="POST")
    with urllib.request.urlopen(req_voice, timeout=5.0) as resp:
        v_data = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200 and v_data.get("status") == "success", f"Voice drop failed: {v_data}"
        # Clean up generated audio test file
        if v_data.get("path") and Path(v_data["path"]).exists():
            Path(v_data["path"]).unlink()
    log_pass("Test 6: POST /api/cockpit/voice_drop -> 200 OK")

    # File Drop test via multipart/form-data boundary
    url_file = f"{BASE_URL}/api/cockpit/file_drop"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="verify_wo0011063.tmp"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
        f"wo0011063-verification-receipt\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    req_file = urllib.request.Request(
        url_file,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req_file, timeout=5.0) as resp:
        f_data = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200 and f_data.get("status") == "success", f"File drop failed: {f_data}"
        tmp_target = REPO_ROOT / "pilot_drops/verify_wo0011063.tmp"
        if tmp_target.exists():
            tmp_target.unlink()
    log_pass("Test 7: POST /api/cockpit/file_drop -> 200 OK")

def test_7_service_status():
    res = subprocess.run(["systemctl", "is-active", "stacklabs-synapse.service"], capture_output=True, text=True)
    if res.stdout.strip() == "active":
        log_pass("Test 8: stacklabs-synapse.service is active (running)")
    else:
        log_fail(f"Test 8: stacklabs-synapse.service status is {res.stdout.strip()}")

def main():
    print("==================================================")
    print("🔍 WO0011063: COCKPIT REBUILD VERIFICATION SUITE")
    print("==================================================")
    test_1_line_count()
    test_2_no_neon_or_filler()
    test_3_get_cockpit()
    test_4_get_queue()
    test_5_post_quickdrop()
    test_6_voice_and_file_drops()
    test_7_service_status()
    print("==================================================")
    print("🎉 ALL 8 VERIFICATION GATES PASSED (100% GREEN)")
    print("==================================================")

if __name__ == "__main__":
    main()
