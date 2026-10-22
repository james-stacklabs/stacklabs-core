#!/usr/bin/env python3
"""
StackLabs Two-Call Verification Script: WO0011225 Purge Listen Slop
Path: /home/james/stacklabs/scripts/verify_wo0011225_purge_listen_slop.py

Empirically verifies:
- Call 1: Zero occurrences of 'CONTINUOUS INTELLIGENCE', 'Continuous Intelligence', 'MASTER DEEP DIVE', or <img> tags in Header.tsx.
- Call 2: Public listen deck and local port 3040 respond HTTP 200.
"""

import sys
import urllib.request
from pathlib import Path

LISTEN_ROOT = Path("/home/james/stacklabs/apps/listen")

def verify_call_1_static_scrub() -> None:
    print("--- [CALL 1: STATIC CODE AUDIT] ---")
    header_file = LISTEN_ROOT / "src" / "components" / "Header.tsx"
    player_file = LISTEN_ROOT / "src" / "components" / "AudioPlayer.tsx"
    tracks_file = LISTEN_ROOT / "src" / "data" / "tracks.ts"
    index_file = LISTEN_ROOT / "index.html"

    # 1. Header has zero img tags and zero slop
    header_content = header_file.read_text(encoding="utf-8")
    assert "<img" not in header_content, "FAIL: <img> tag found in Header.tsx"
    assert "CONTINUOUS INTELLIGENCE" not in header_content, "FAIL: CONTINUOUS INTELLIGENCE found in Header.tsx"
    assert "400MS LOOP" not in header_content, "FAIL: 400MS LOOP found in Header.tsx"
    print("✔ Header.tsx: Zero img tags, zero continuous intelligence slop, zero robotic telemetry pills.")

    # 2. AudioPlayer has zero MASTER DEEP DIVE badge
    player_content = player_file.read_text(encoding="utf-8")
    assert "MASTER DEEP DIVE" not in player_content, "FAIL: MASTER DEEP DIVE found in AudioPlayer.tsx"
    print("✔ AudioPlayer.tsx: Zero MASTER DEEP DIVE badges.")

    # 3. tracks.ts has zero continuous intelligence
    tracks_content = tracks_file.read_text(encoding="utf-8")
    assert "Continuous Intelligence" not in tracks_content, "FAIL: Continuous Intelligence found in tracks.ts"
    assert "FaaS Lexical Anomaly Detection" not in tracks_content, "FAIL: FaaS Lexical Anomaly Detection found in tracks.ts"
    print("✔ tracks.ts: Cleaned subtitle and chapter titles.")

    # 4. index.html has clean title
    index_content = index_file.read_text(encoding="utf-8")
    assert "<title>StackLabs Listen</title>" in index_content, "FAIL: Clean title missing in index.html"
    print("✔ index.html: Title strictly 'StackLabs Listen'.\n")


def verify_call_2_live_endpoints() -> None:
    print("--- [CALL 2: LIVE ENDPOINT VERIFICATION] ---")
    for probe_url in ["http://127.0.0.1:3040/", "https://listen.stacklabsllc.com/"]:
        req = urllib.request.Request(probe_url, headers={"User-Agent": "StackLabs-Verifier/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"✔ Probe {probe_url} -> HTTP {resp.status}")
                assert resp.status == 200
        except Exception as e:
            print(f"FAIL: Probe {probe_url} failed: {e}")
            sys.exit(1)
    print("✔ CALL 2 PASSED: All endpoints healthy.\n")


if __name__ == "__main__":
    print("=================================================================")
    print("STACKLABS TWO-CALL VERIFICATION: WO0011225 PURGE LISTEN SLOP")
    print("=================================================================")
    verify_call_1_static_scrub()
    verify_call_2_live_endpoints()
    print("🎉 ALL CHECKS PASSED EMPIRICALLY.")
    sys.exit(0)
