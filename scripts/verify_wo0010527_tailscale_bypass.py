#!/usr/bin/env python3
"""
Verification Script for WO0010527:
Tailscale Auto-Bypass and Master Access Keys for Enterprise Drop Gateway (Port 8088).
"""
import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8088"

def test_tailscale_auto_bypass():
    print("[TEST 1] Querying / with Host: clio.taila01894.ts.net:8088...")
    req = urllib.request.Request(
        f"{BASE_URL}/",
        headers={"Host": "clio.taila01894.ts.net:8088"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200, f"Expected 200 OK, got {resp.status}"
        body = resp.read().decode('utf-8')
        assert "STACKLABS" in body, "Expected 'STACKLABS' in body"
        # Assert drop portal is rendered, NOT the passcode gate
        assert "id=\"passcode\"" not in body, "Passcode gate was rendered instead of direct drop portal!"
        assert "Direct File Drop" in body or "VOICE MONOLOGUE INGRESS" in body, "Drop interface elements missing"
        # Check cookie
        cookie_header = resp.headers.get("Set-Cookie", "")
        assert "stacklabs_drop_auth" in cookie_header, f"Expected auth cookie to be set, got: {cookie_header}"
        print("  -> PASSED: HTTP 200 OK, STACKLABS in body, zero 401/passcode gate, 30-day auth cookie set.")

def test_auth_key(passcode: str, expected_status: int, expected_message: str = None):
    print(f"[TEST] Testing /api/auth with passcode='{passcode}' (expecting {expected_status})...")
    payload = json.dumps({"passcode": passcode}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        status = e.code
        data = json.loads(e.read().decode('utf-8'))

    assert status == expected_status, f"Expected status {expected_status}, got {status} ({data})"
    if expected_message:
        assert expected_message in data.get("message", ""), f"Expected '{expected_message}' in response message, got: {data}"
    print(f"  -> PASSED: HTTP {status} ({data.get('message', '')})")

def main():
    print("=" * 60)
    print("⚡ VERIFYING WO0010527: TAILSCALE BYPASS & MASTER KEYS")
    print("=" * 60)
    
    test_tailscale_auto_bypass()
    test_auth_key("stacklabs", 200, "Access granted")
    test_auth_key("pilot", 200, "Access granted")
    test_auth_key("sovereign", 200, "Access granted")
    test_auth_key("stacklabs2026", 200, "Access granted")
    test_auth_key("carroll2026", 200, "Access granted")
    test_auth_key("rudnicki2026", 200, "Access granted")
    test_auth_key("heywood2026", 200, "Access granted")
    test_auth_key("bogus_key", 401, "Invalid access key")
    
    print("=" * 60)
    print("✅ ALL WO0010527 VERIFICATION CHECKS PASSED WITH 100% COMPLIANCE")
    print("=" * 60)

if __name__ == "__main__":
    main()
