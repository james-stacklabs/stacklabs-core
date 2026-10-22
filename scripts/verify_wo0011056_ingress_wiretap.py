#!/usr/bin/env python3
"""
verify_wo0011056_ingress_wiretap.py
Verification gate for WO0011056: Ingress mapping and wiretap logging.
"""
import sys
import json
import time
import requests
from pathlib import Path

def main():
    print("==================================================")
    print("⚡ VERIFYING WO0011056 ON CLIO METAL")
    print("==================================================")

    # 1. Verify cloudflared config
    cfg = Path("/etc/cloudflared/config.yml")
    if not cfg.exists():
        print("❌ FAIL: /etc/cloudflared/config.yml does not exist")
        sys.exit(1)
    content = cfg.read_text()
    if "arena.stacklabsllc.com" not in content or "http://localhost:3025" not in content:
        print("❌ FAIL: arena.stacklabsllc.com not mapped to port 3025 in config")
        sys.exit(1)
    print("✔ Cloudflare config correctly routes arena.stacklabsllc.com -> port 3025")

    # 2. Test Wiretap API endpoint directly
    wiretap_url = "http://127.0.0.1:3033/api/benchmark/wiretap"
    test_payload = {
        "ref": "test_runner",
        "event": "VERIFY_RUN",
        "tab": "benchmark",
        "details": {"source": "metal_verification"}
    }
    try:
        res = requests.post(wiretap_url, json=test_payload, timeout=3)
        if res.status_code != 200:
            print(f"❌ FAIL: Wiretap endpoint returned status {res.status_code}")
            sys.exit(1)
        data = res.json()
        if data.get("status") != "ACK":
            print(f"❌ FAIL: Wiretap returned unexpected payload: {data}")
            sys.exit(1)
        print("✔ Wiretap API acknowledged event receipt with HTTP 200 ACK")
    except Exception as e:
        print(f"❌ FAIL: Error connecting to wiretap endpoint: {e}")
        sys.exit(1)

    # 3. Verify entry in log file
    log_file = Path("/home/james/stacklabs/logs/cmdb_wiretap.log")
    if not log_file.exists():
        print("❌ FAIL: Log file does not exist")
        sys.exit(1)
    
    last_line = log_file.read_text().strip().split("\n")[-1]
    parsed = json.loads(last_line)
    if parsed.get("ref") != "test_runner":
        print(f"❌ FAIL: Last log entry does not match test payload: {parsed}")
        sys.exit(1)
    print(f"✔ Wiretap log receipt verified on disk: {log_file}")

    print("==================================================")
    print("✅ WO0011056 VERIFIED: ALL GATES GREEN")
    print("==================================================")

if __name__ == "__main__":
    main()
