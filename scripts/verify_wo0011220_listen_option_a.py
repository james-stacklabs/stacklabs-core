#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Verification Suite for WO0011220: Option A Purge Legacy Tracks & Align Listen Portal Architecture
Path: /home/james/stacklabs/scripts/verify_wo0011220_listen_option_a.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
Host: Clio (clio / Dedicated Linux Host / 100.96.77.20)
Governing Standards: Invariant 15 (Two-Call Mandate), 32 (Law of "I"), 35 (.venv), 50
"""

import re
import sys
from pathlib import Path

import requests

REPO_ROOT = Path("/home/james/stacklabs")
TRACKS_FILE = REPO_ROOT / "apps" / "listen" / "src" / "data" / "tracks.ts"
PLAYER_FILE = REPO_ROOT / "apps" / "listen" / "src" / "components" / "AudioPlayer.tsx"
SEARCH_FILE = REPO_ROOT / "apps" / "listen" / "src" / "components" / "BroadcastSearchModal.tsx"
LISTEN_BASE = "http://127.0.0.1:3040"

EXPECTED_TRACK_IDS = [
    "decoding-slang-to-beat-wall-street-19m",
    "why-llms-are-calculators-not-databases",
    "swanson-colliders-map-cause-and-effect-6m",
    "why-vector-databases-are-obsolete-25m",
    "swanson-collider-connects-hidden-knowledge-22m",
]

FORBIDDEN_TOKENS = [
    "empathy-as-architecture-paul-rudnicki",
    "sentinel-swarms-executive-brief",
    "oil-pipeline-architecture-deep-dive",
    "paul-trading-strategy",
    "trading-media-velocity-over-speed",
    "horizon-executive-deep-dive",
    "paul_visionary_surveyor_james_train.jpg",
    "Paul Rudnicki",
    "Pawel Rudnicki",
    "bare metal",
]


def call1_mutation_source_audit() -> None:
    print("[VERIFICATION-CALL-1] Auditing tracks.ts, AudioPlayer.tsx, and BroadcastSearchModal.tsx...")
    tracks_src = TRACKS_FILE.read_text(encoding="utf-8")
    player_src = PLAYER_FILE.read_text(encoding="utf-8")
    search_src = SEARCH_FILE.read_text(encoding="utf-8")

    # 1. Audit Forbidden Tokens
    for token in FORBIDDEN_TOKENS:
        if token in tracks_src:
            print(f"FAILED: Forbidden token '{token}' found in {TRACKS_FILE}", file=sys.stderr)
            sys.exit(1)
        if token in player_src:
            print(f"FAILED: Forbidden token '{token}' found in {PLAYER_FILE}", file=sys.stderr)
            sys.exit(1)
        if token in search_src:
            print(f"FAILED: Forbidden token '{token}' found in {SEARCH_FILE}", file=sys.stderr)
            sys.exit(1)

    # 2. Audit Expected Track IDs
    for tid in EXPECTED_TRACK_IDS:
        if f"id: '{tid}'" not in tracks_src:
            print(f"FAILED: Expected track ID '{tid}' missing from {TRACKS_FILE}", file=sys.stderr)
            sys.exit(1)

    # 3. Count tracks in TRACKS array
    track_matches = re.findall(r"id:\s*'([a-z0-9\-]+)'", tracks_src)
    # The first 5 are track IDs
    active_tracks = [t for t in track_matches if t in EXPECTED_TRACK_IDS]
    if len(active_tracks) != 5:
        print(f"FAILED: Expected exactly 5 active tracks in {TRACKS_FILE}, found {len(active_tracks)}", file=sys.stderr)
        sys.exit(1)

    # 4. Count concept IDs in THESIS_CONCEPTS array
    concept_matches = re.findall(r"id:\s*'concept-([a-z0-9\-]+)'", tracks_src)
    if len(concept_matches) != 13:
        print(f"FAILED: Expected exactly 13 thesis concepts in {TRACKS_FILE}, found {len(concept_matches)}", file=sys.stderr)
        sys.exit(1)

    print(f"PASS Call 1: tracks.ts contains exactly {len(active_tracks)} institutional tracks and {len(concept_matches)} concepts with zero forbidden tokens.")


def call2_readback_http_probe() -> None:
    print("[VERIFICATION-CALL-2] Probing Listen server on Port 3040 via HTTP...")
    url = f"{LISTEN_BASE}/"
    try:
        resp = requests.get(url, timeout=5.0)
        if resp.status_code != 200:
            print(f"FAILED: Server returned HTTP {resp.status_code}", file=sys.stderr)
            sys.exit(1)

        body = resp.text
        if "<!doctype html>" not in body.lower() and "<div id=\"root\"" not in body:
            print("FAILED: Response body missing root HTML structure", file=sys.stderr)
            sys.exit(1)

        print(f"PASS Call 2: Verified HTTP 200 OK response from {url}.")
    except Exception as exc:
        print(f"FAILED: Could not connect to {url}: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    call1_mutation_source_audit()
    call2_readback_http_probe()
    print("\n=== ALL WO0011220 OPTION A AUDIT CHECKS PASSED ===")


if __name__ == "__main__":
    main()
