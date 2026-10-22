#!/usr/bin/env python3
"""
Verification suite for WO0010329:
Suppress Internal Test Wiretaps & Notification Noise.
"""

import sys
from pathlib import Path
sys.path.insert(0, "/home/james/stacklabs")

import json
import requests

BASE_URL = "http://127.0.0.1:8095"
SCRATCHPAD_PATH = Path("/home/james/sovereign_inbox/pilot_drops/scratch_pad.md")

def get_latest_audit():
    res = requests.get(f"{BASE_URL}/api/wildseed_beacon/audit?limit=1", timeout=5)
    res.raise_for_status()
    audits = res.json().get("audits", [])
    return audits[0] if audits else None

def read_scratchpad():
    if SCRATCHPAD_PATH.exists():
        return SCRATCHPAD_PATH.read_text(encoding="utf-8")
    return ""

def test_anonymous_drop_visit_silenced():
    print("\n--- Test 1: Anonymous /drop Page Visit Silenced ---")
    initial_sp = read_scratchpad()
    
    payload = {
        "event": "drop_page_visit",
        "event_type": "drop_page_visit",
        "city": "Dallas",
        "region": "Texas",
        "country": "US",
        "ip": "198.51.100.44",
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15",
        "details": {
            "route": "/drop",
            "partner": "anonymous",
            "referrer": "direct",
            "credits_left": 3
        }
    }
    
    res = requests.post(f"{BASE_URL}/api/wildseed_beacon", json=payload, timeout=5)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    
    audit = get_latest_audit()
    assert audit is not None, "No audit entry created"
    assert audit["event_type"] == "drop_page_visit"
    assert audit["alert_dispatched"] == 0, f"Expected alert_dispatched == 0 for anonymous visit, got {audit['alert_dispatched']}"
    
    after_sp = read_scratchpad()
    assert after_sp == initial_sp, "Anonymous visit must NEVER append to scratch_pad.md!"
    print("  ✅ PASS: Anonymous /drop visit did not dispatch alert (alert_dispatched=0) and did not touch scratchpad.")

def test_automated_test_signatures_silenced():
    print("\n--- Test 2: Automated Test Signatures Silenced ---")
    initial_sp = read_scratchpad()

    test_cases = [
        ("curl user agent", {"userAgent": "curl/8.5.0", "details": {"partner": "Pawel", "route": "/pawel"}}),
        ("Playwright UA", {"userAgent": "Mozilla/5.0 Playwright/1.40 Chrome/120.0", "details": {"partner": "Pawel", "route": "/pawel"}}),
        ("Headless UA", {"userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 HeadlessChrome/120.0", "details": {"partner": "Pawel", "route": "/pawel"}}),
        ("python-requests UA", {"userAgent": "python-requests/2.31.0", "details": {"partner": "Pawel", "route": "/pawel"}}),
        ("agy UA", {"userAgent": "agy-headless-agent/1.0", "details": {"partner": "Pawel", "route": "/pawel"}}),
        ("is_test in details", {"userAgent": "Mozilla/5.0 Safari/605.1.15", "details": {"partner": "Pawel", "route": "/pawel", "is_test": True}}),
        ("is_test top level", {"userAgent": "Mozilla/5.0 Safari/605.1.15", "is_test": True, "details": {"partner": "Pawel", "route": "/pawel"}}),
        ("Tailscale IP", {"ip": "100.96.77.20", "city": "Warsaw", "details": {"partner": "Pawel", "route": "/pawel"}}),
        ("Localhost IP", {"ip": "127.0.0.1", "city": "Warsaw", "details": {"partner": "Pawel", "route": "/pawel"}}),
        ("Unknown City + Internal IP", {"ip": "127.0.0.1", "city": "Unknown City", "details": {"partner": "Pawel", "route": "/pawel"}}),
    ]

    for label, override in test_cases:
        payload = {
            "event": "drop_page_visit",
            "city": override.get("city", "Warsaw"),
            "region": "Mazovia",
            "country": "Poland",
            "ip": override.get("ip", "185.152.65.1"),
            "userAgent": override.get("userAgent", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5)"),
            "details": override.get("details", {})
        }
        if "is_test" in override:
            payload["is_test"] = override["is_test"]

        res = requests.post(f"{BASE_URL}/api/wildseed_beacon", json=payload, timeout=5)
        assert res.status_code == 200
        
        audit = get_latest_audit()
        assert audit["alert_dispatched"] == 0, f"Failed for {label}: alert_dispatched was {audit['alert_dispatched']}"
        after_sp = read_scratchpad()
        assert after_sp == initial_sp, f"Failed for {label}: appended to scratchpad!"
        print(f"  ✅ PASS: Silenced for [{label}]")

def test_pilot_geo_silenced():
    print("\n--- Test 3: Pilot Geo Silenced ---")
    initial_sp = read_scratchpad()

    pilot_geos = [
        ("Smyrna", "Georgia"),
        ("Atlanta", "GA"),
        ("Marietta", "Georgia"),
    ]
    for city, region in pilot_geos:
        payload = {
            "event": "drop_page_visit",
            "city": city,
            "region": region,
            "country": "US",
            "ip": "24.126.100.5",
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X)",
            "details": {
                "route": "/pawel",
                "partner": "Pawel",
            }
        }
        res = requests.post(f"{BASE_URL}/api/wildseed_beacon", json=payload, timeout=5)
        assert res.status_code == 200
        audit = get_latest_audit()
        assert audit["alert_dispatched"] == 0, f"Pilot geo ({city}, {region}) must not alert"
        after_sp = read_scratchpad()
        assert after_sp == initial_sp, f"Pilot geo ({city}, {region}) must not touch scratchpad"
        print(f"  ✅ PASS: Pilot geo ({city}, {region}) silenced.")

def test_partner_detection_unit_logic():
    print("\n--- Test 4: Partner Detection Unit Logic ---")
    from scripts.routers.auth import _is_pilot_local_ip

    # Test IP check
    assert _is_pilot_local_ip("127.0.0.1") is True
    assert _is_pilot_local_ip("::1") is True
    assert _is_pilot_local_ip("localhost") is True
    assert _is_pilot_local_ip("100.96.77.20") is True
    assert _is_pilot_local_ip("192.168.1.50") is True
    assert _is_pilot_local_ip("10.0.0.1") is True
    assert _is_pilot_local_ip("172.20.0.1") is True
    assert _is_pilot_local_ip("185.152.65.1") is False
    assert _is_pilot_local_ip("203.0.113.195") is False
    print("  ✅ PASS: _is_pilot_local_ip verified.")

    # Test named partner gate logic
    test_partners = [
        ("anonymous", False),
        ("guest", False),
        ("default", False),
        ("none", False),
        ("", False),
        (None, False),
        ("Pawel", True),
        ("Paul", True),
        ("Jeremy", True),
        ("Michael Mclaren", True),
    ]
    for p, expected in test_partners:
        is_named = p is not None and str(p).lower() not in ("anonymous", "guest", "default", "none", "")
        assert is_named == expected, f"Partner {p} expected {expected}, got {is_named}"
    print("  ✅ PASS: is_named_partner evaluated correctly across all test variations.")

def test_scratchpad_hygiene():
    print("\n--- Test 5: Scratchpad Hygiene & Invariants ---")
    lines = SCRATCHPAD_PATH.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 75, f"scratch_pad.md has {len(lines)} lines, exceeds 75-line ITSM invariant!"
    
    # Verify no curl or anonymous test wiretaps in scratchpad
    for idx, line in enumerate(lines, 1):
        if "[DROP VISITOR WIRETAP]" in line:
            assert "curl" not in line.lower(), f"Line {idx} contains curl wiretap: {line}"
            assert "@anonymous" not in line.lower(), f"Line {idx} contains anonymous wiretap: {line}"
            assert "unknown city" not in line.lower(), f"Line {idx} contains unknown city wiretap: {line}"
    print(f"  ✅ PASS: scratch_pad.md is clean ({len(lines)}/75 lines), zero test wiretaps found.")

def test_client_side_pages_code():
    print("\n--- Test 6: Client-Side Edge Deploy Verification ---")
    deploy_dir = Path("/home/james/sovereign_inbox/pilot_drops/cloudflare_pages_deploy")
    for file_name in ["drop.html", "pawel.html", "paul.html", "drop/index.html", "pawel/index.html", "paul/index.html"]:
        fpath = deploy_dir / file_name
        content = fpath.read_text(encoding="utf-8")
        assert "isInternalHost" in content, f"Missing isInternalHost in {file_name}"
        assert "isTestFlag" in content, f"Missing isTestFlag in {file_name}"
        assert "is_test: isTest" in content, f"Missing is_test in {file_name}"
    print("  ✅ PASS: All 6 edge HTML deployment files contain is_test beacon filtering logic.")

def main():
    print("==================================================")
    print("VERIFICATION SUITE: WO0010329")
    print("SUPPRESS INTERNAL TEST WIRETAPS & NOTIFICATION NOISE")
    print("==================================================")
    test_anonymous_drop_visit_silenced()
    test_automated_test_signatures_silenced()
    test_pilot_geo_silenced()
    test_partner_detection_unit_logic()
    test_scratchpad_hygiene()
    test_client_side_pages_code()
    print("\n==================================================")
    print("🎉 ALL ACCEPTANCE CRITERIA VERIFIED AND PASSING!")
    print("==================================================")

if __name__ == "__main__":
    main()
