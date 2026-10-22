#!/usr/bin/env python3
"""
Verification Suite for WO0010908:
Deploy The Sentinel Swarms Audio and Slide Deck to Listen (Port 3040)
"""

import os
import sys
import urllib.request
import urllib.error

LISTEN_PORT = 3040
BASE_URL = f"http://127.0.0.1:{LISTEN_PORT}"

REQUIRED_FILES = [
    ("/home/james/stacklabs/apps/listen/public/audio/Trading_Stocks_Like_Oil_Refineries.m4a", 3463823),
    ("/home/james/stacklabs/apps/listen/public/audio/Oil_Pipeline_Architecture_for_Algorithmic_Trading.m4a", 45654690),
    ("/home/james/stacklabs/apps/listen/public/assets/The_Sentinel_Swarms.pdf", 17737608),
    ("/home/james/stacklabs/apps/listen/public/documents/The_Sentinel_Swarms.pdf", 17737608),
]

HTTP_ENDPOINTS = [
    ("/", 200, "text/html"),
    ("/audio/Trading_Stocks_Like_Oil_Refineries.m4a", 200, "audio/mp4"),
    ("/audio/Oil_Pipeline_Architecture_for_Algorithmic_Trading.m4a", 200, "audio/mp4"),
    ("/assets/The_Sentinel_Swarms.pdf", 200, "application/pdf"),
    ("/documents/The_Sentinel_Swarms.pdf", 200, "application/pdf"),
]

def check_files():
    print("=== [1/3] Checking Physical File Assets on Metal ===")
    all_ok = True
    for path, expected_size in REQUIRED_FILES:
        if not os.path.exists(path):
            print(f"❌ Missing file: {path}")
            all_ok = False
            continue
        actual_size = os.path.getsize(path)
        if actual_size != expected_size:
            print(f"❌ Size mismatch for {path}: expected {expected_size}, got {actual_size}")
            all_ok = False
        else:
            print(f"✅ Verified {os.path.basename(path)} ({actual_size:,} bytes)")
    return all_ok

def check_tracks_ts():
    print("\n=== [2/3] Checking tracks.ts Track Registrations ===")
    tracks_ts_path = "/home/james/stacklabs/apps/listen/src/data/tracks.ts"
    if not os.path.exists(tracks_ts_path):
        print(f"❌ Missing tracks.ts at {tracks_ts_path}")
        return False
    with open(tracks_ts_path, "r", encoding="utf-8") as f:
        content = f.read()

    checks = [
        "sentinel-swarms-executive-brief",
        "oil-pipeline-architecture-deep-dive",
        "/audio/Trading_Stocks_Like_Oil_Refineries.m4a",
        "/audio/Oil_Pipeline_Architecture_for_Algorithmic_Trading.m4a",
    ]
    all_ok = True
    for c in checks:
        if c in content:
            print(f"✅ Found registration: {c}")
        else:
            print(f"❌ Missing registration: {c}")
            all_ok = False
    return all_ok

def check_http():
    print(f"\n=== [3/3] Checking HTTP Endpoints on {BASE_URL} ===")
    all_ok = True
    for route, expected_status, expected_mime in HTTP_ENDPOINTS:
        url = f"{BASE_URL}{route}"
        req = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
                content_length = resp.headers.get("Content-Length", "unknown")
                if status == expected_status and expected_mime in content_type:
                    print(f"✅ HEAD {route} -> HTTP {status} [{content_type}] ({content_length} bytes)")
                else:
                    print(f"❌ HEAD {route} -> HTTP {status} [{content_type}] (expected {expected_status}, {expected_mime})")
                    all_ok = False
        except Exception as e:
            print(f"❌ HEAD {route} failed: {e}")
            all_ok = False
    return all_ok

def main():
    print("================================================================")
    print("WO0010908: The Sentinel Swarms Listen Deployment Verification")
    print("================================================================")
    ok1 = check_files()
    ok2 = check_tracks_ts()
    ok3 = check_http()

    if ok1 and ok2 and ok3:
        print("\n🎯 ALL AUDIT CHECKS PASSED ON CLIO METAL (100% OK TO GO)")
        sys.exit(0)
    else:
        print("\n❌ VERIFICATION FAILED ON CLIO METAL")
        sys.exit(1)

if __name__ == "__main__":
    main()
