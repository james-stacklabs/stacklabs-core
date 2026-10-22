#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Verification Suite for WO0011219: Purge Paul Briefing Cosplay & Align Listen Branding
Path: /home/james/stacklabs/scripts/verify_wo0011219_listen_branding.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
Host: Clio (clio / Dedicated Linux Host / 100.96.77.20)
Governing Standards: Invariant 15 (Two-Call Mandate), 32 (Law of "I"), 35 (.venv), 50
"""

import re
import sys
from pathlib import Path

import requests

REPO_ROOT = Path("/home/james/stacklabs")
HEADER_FILE = REPO_ROOT / "apps" / "listen" / "src" / "components" / "Header.tsx"
PLAYLIST_FILE = REPO_ROOT / "apps" / "listen" / "src" / "components" / "PlaylistDrawer.tsx"
LISTEN_BASE = "http://127.0.0.1:3040"


def call1_mutation_source_audit() -> None:
    print("[VERIFICATION-CALL-1] Auditing component source files for purged cosplay tokens...")
    header_src = HEADER_FILE.read_text(encoding="utf-8")
    playlist_src = PLAYLIST_FILE.read_text(encoding="utf-8")

    if re.search(r"PAUL\s+RUDNICKI", header_src, re.IGNORECASE):
        print(f"FAILED: 'PAUL RUDNICKI' found in {HEADER_FILE}", file=sys.stderr)
        sys.exit(1)

    if re.search(r"Paul\s+Rudnicki", playlist_src, re.IGNORECASE):
        print(f"FAILED: 'Paul Rudnicki' found in {PLAYLIST_FILE}", file=sys.stderr)
        sys.exit(1)

    if "bare metal" in playlist_src.lower():
        print(f"FAILED: Banned token 'bare metal' found in {PLAYLIST_FILE}", file=sys.stderr)
        sys.exit(1)

    if "paul_visionary_surveyor_james_train.jpg" in playlist_src:
        print(f"FAILED: Legacy image reference found in {PLAYLIST_FILE}", file=sys.stderr)
        sys.exit(1)

    print("PASS Call 1: Components are 100% clean of 'Paul Rudnicki', 'bare metal', and legacy imagery.")


def call2_readback_http_probe() -> None:
    print("[VERIFICATION-CALL-2] Probing Listen server on Port 3040 via HTTP...")
    url = f"{LISTEN_BASE}/"
    try:
        resp = requests.get(url, timeout=5.0)
        if resp.status_code != 200:
            print(f"FAILED: Server returned HTTP {resp.status_code}", file=sys.stderr)
            sys.exit(1)

        print(f"PASS Call 2: Verified HTTP 200 OK response from {url}.")
    except Exception as exc:
        print(f"FAILED: Could not connect to {url}: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    call1_mutation_source_audit()
    call2_readback_http_probe()
    print("\n=== ALL WO0011219 BRANDING PURGE CHECKS PASSED ===")


if __name__ == "__main__":
    main()
