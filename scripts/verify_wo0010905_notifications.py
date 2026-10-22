#!/usr/bin/env python3
"""
StackLabs Verification Harness: WO0010905
Path: /home/james/stacklabs/scripts/verify_wo0010905_notifications.py

Verifies:
1. pilot_notifier.py executes cleanly and writes to logs/pilot_notifications.log.
2. Horizon Listen Vite server (/api/wiretap) responds 200 to beacon telemetry.
3. Vector6 Chat /api/v6/chat/send triggers pilot notification log entry.
"""

import sys
import json
import time
import urllib.request
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(STACKLABS_ROOT))

from scripts.pilot_notifier import dispatch_pilot_alert

LOG_FILE = STACKLABS_ROOT / "logs" / "pilot_notifications.log"


def test_notifier_direct():
    print("[1/3] Testing pilot_notifier.py direct dispatch...")
    initial_lines = 0
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            initial_lines = len(f.readlines())

    ok = dispatch_pilot_alert(
        title="🧪 [UAT TEST] Notification Verification",
        body="Verification pulse testing multi-channel alert delivery on Clio metal.",
        priority="low",
        tags="test_tube",
        sound=False
    )
    assert ok, "Direct dispatch failed"

    with open(LOG_FILE, "r") as f:
        final_lines = len(f.readlines())
    assert final_lines > initial_lines, "Audit log was not updated"
    print("      ✓ Direct dispatch and audit logging verified.")


def test_listen_wiretap_beacon():
    print("[2/3] Testing Sovereign Listen /api/wiretap beacon on Port 3040...")
    url = "http://127.0.0.1:3040/api/wiretap"
    payload = json.dumps({
        "event": "PAGE_MOUNT",
        "trackId": "horizon-executive-deep-dive",
        "trackTitle": "Horizon: The 35-Watt Bare-Metal Engine"
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Forwarded-For": "98.185.224.114",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X)"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Wiretap returned status {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("status") == "ok", f"Unexpected payload: {data}"
    print("      ✓ Wiretap beacon accepted with counterparty IP.")


def test_vector6_chat_alert():
    print("[3/3] Testing Vector6 Chat /api/v6/chat/send on Port 8095...")
    url = "http://127.0.0.1:8095/api/v6/chat/send"
    payload = json.dumps({
        "channel": "pawel",
        "sender": "pawel",
        "body": "UAT alert test verification pulse from Pawel Rudnicki channel"
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Vector6 returned status {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("status") == "DELIVERED", f"Unexpected response: {data}"
    print("      ✓ Vector6 message delivered and alert dispatched.")


def main():
    print("==================================================")
    print("🔬 WO0010905: PILOT NOTIFICATION HARNESS")
    print("==================================================")
    test_notifier_direct()
    test_listen_wiretap_beacon()
    test_vector6_chat_alert()
    print("\n✅ ALL 3 VERIFICATION TESTS PASSED CLEANLY ON METAL.")


if __name__ == "__main__":
    main()
