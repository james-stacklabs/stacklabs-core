#!/usr/bin/env python3
"""
StackLabs Two-Call Verification Script: WO0011224 Purge Sovereign Alerts
Path: /home/james/stacklabs/scripts/verify_wo0011224_purge_sovereign_alerts.py

Empirically verifies:
- Call 1: Zero occurrences of 'sovereign-pilot-alerts' across target codebase files.
- Call 2: Live test notification dispatch via pilot_notifier.py targeting 'stacklabs-pilot-alerts' returns HTTP 200.
- Call 3: Public listen deck and local port 3040 respond HTTP 200.
"""

import os
import sys
import subprocess
import urllib.request
from pathlib import Path

TARGET_FILES = [
    Path("/home/james/stacklabs/scripts/pilot_notifier.py"),
    Path("/home/james/stacklabs/apps/listen/vite.config.ts"),
    Path("/home/james/stacklabs/scripts/clio-notify.sh"),
    Path("/home/james/stacklabs/apps/listen/src/services/wiretap.ts"),
]

def verify_call_1_codebase_purge() -> None:
    print("--- [CALL 1: STATIC PURITY AUDIT] ---")
    violations = []
    for f in TARGET_FILES:
        if not f.exists():
            print(f"FAIL: Expected file {f} does not exist.")
            sys.exit(1)
        content = f.read_text(encoding="utf-8")
        if "sovereign-pilot-alerts" in content or "sovereign" in content.lower():
            violations.append(str(f))
        if "stacklabs-pilot-alerts" not in content and f.suffix in [".py", ".ts", ".sh"]:
            violations.append(f"{f} missing stacklabs-pilot-alerts")

    if violations:
        print(f"FAIL: Cosplay violations or missing stacklabs-pilot-alerts detected: {violations}")
        sys.exit(1)

    print("✔ All target files verified 100% free of 'sovereign-pilot-alerts'.")
    print("✔ Canonical 'stacklabs-pilot-alerts' topic confirmed across all targets.\n")


def verify_call_2_live_ntfy_delivery() -> None:
    print("--- [CALL 2: LIVE NTFY PUSH DISPATCH TEST] ---")
    python_bin = "/home/james/stacklabs/.venv/bin/python3"
    notifier_script = "/home/james/stacklabs/scripts/pilot_notifier.py"

    cmd = [
        python_bin,
        notifier_script,
        "--title", "StackLabs Telemetry Verification",
        "--body", "Empirical proof of WO0011224 stacklabs-pilot-alerts re-anchoring.",
        "--priority", "low",
        "--tags", "white_check_mark,shield",
        "--no-sound"
    ]
    try:
        subprocess.check_call(cmd)
        print("✔ Dispatched test alert via pilot_notifier.py.")
    except Exception as e:
        print(f"FAIL: pilot_notifier.py execution failed: {e}")
        sys.exit(1)

    # Check ntfy.sh direct probe
    url = "https://ntfy.sh/stacklabs-pilot-alerts/raw?poll=1&since=5m"
    req = urllib.request.Request(url, headers={"User-Agent": "StackLabs-Verifier/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode("utf-8")
            assert "Empirical proof of WO0011224" in data, "Notification not found in raw poll"
            print("✔ Verified test alert received by https://ntfy.sh/stacklabs-pilot-alerts.")
    except Exception as e:
        print(f"FAIL: Could not poll ntfy.sh/stacklabs-pilot-alerts: {e}")
        sys.exit(1)

    print("✔ CALL 2 PASSED: Real-time push verified.\n")


def verify_call_3_listen_endpoints() -> None:
    print("--- [CALL 3: LISTEN SERVICE HEALTH PROBE] ---")
    for probe_url in ["http://127.0.0.1:3040/", "https://listen.stacklabsllc.com/"]:
        req = urllib.request.Request(probe_url, headers={"User-Agent": "StackLabs-Verifier/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"✔ Probe {probe_url} -> HTTP {resp.status}")
                assert resp.status == 200
        except Exception as e:
            print(f"FAIL: Probe {probe_url} failed: {e}")
            sys.exit(1)
    print("✔ CALL 3 PASSED: Listen deck active on local port and public edge.\n")


if __name__ == "__main__":
    print("=================================================================")
    print("STACKLABS TWO-CALL VERIFICATION: WO0011224 PURGE SOVEREIGN ALERTS")
    print("=================================================================")
    verify_call_1_codebase_purge()
    verify_call_2_live_ntfy_delivery()
    verify_call_3_listen_endpoints()
    print("🎉 ALL TWO-CALL CHECKS PASSED EMPIRICALLY.")
    sys.exit(0)
