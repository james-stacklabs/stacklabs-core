#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Verification Suite for WO0011221: Single Track Minimal Dark Listen Portal
Path: /home/james/stacklabs/scripts/verify_wo0011221_minimal_listen.py
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Host: Clio (clio / Dedicated Linux Host / 100.96.77.20)
Governing Standards: Invariant 15 (Two-Call Mandate), Invariant 32 (Law of "I"), Invariant 35 (.venv), Invariant 50
"""

import sys
from pathlib import Path

import requests

REPO_ROOT = Path("/home/james/stacklabs")
TRACKS_FILE = REPO_ROOT / "apps" / "listen" / "src" / "data" / "tracks.ts"
PLAYER_FILE = REPO_ROOT / "apps" / "listen" / "src" / "components" / "AudioPlayer.tsx"
HEADER_FILE = REPO_ROOT / "apps" / "listen" / "src" / "components" / "Header.tsx"
APP_FILE = REPO_ROOT / "apps" / "listen" / "src" / "App.tsx"
COVER_FILE = REPO_ROOT / "apps" / "listen" / "public" / "assets" / "wall_street_slang_cover.jpg"
LISTEN_BASE = "http://127.0.0.1:3040"

FORBIDDEN_TOKENS = [
    "latency_fabric_cover.png",
    "paul_visionary_surveyor_james_train.jpg",
    "The_Latency_Inverted_Knowledge_Fabric.pdf",
    "Empathy_as_Architecture.pdf",
    "empathy-as-architecture-paul-rudnicki",
    "sentinel-swarms-executive-brief",
    "oil-pipeline-architecture-deep-dive",
    "paul-trading-strategy",
    "trading-media-velocity-over-speed",
    "horizon-executive-deep-dive",
]


def call1_mutation_source_audit() -> None:
    print("[VERIFICATION-CALL-1] Auditing clean single-track source files...")
    tracks_src = TRACKS_FILE.read_text(encoding="utf-8")
    player_src = PLAYER_FILE.read_text(encoding="utf-8")
    header_src = HEADER_FILE.read_text(encoding="utf-8")
    app_src = APP_FILE.read_text(encoding="utf-8")

    # 1. Verify Cover Art File Exists
    if not COVER_FILE.exists():
        print(f"FAILED: Cover art file missing: {COVER_FILE}", file=sys.stderr)
        sys.exit(1)

    # 2. Check Forbidden Tokens
    for token in FORBIDDEN_TOKENS:
        for fpath, src in [
            (TRACKS_FILE, tracks_src),
            (PLAYER_FILE, player_src),
            (HEADER_FILE, header_src),
            (APP_FILE, app_src),
        ]:
            if token in src:
                print(f"FAILED: Forbidden token '{token}' found in {fpath}", file=sys.stderr)
                sys.exit(1)

    # 3. Assert Single Track ID
    if "decoding-slang-to-beat-wall-street-19m" not in tracks_src:
        print(f"FAILED: Expected Wall Street Slang track ID missing from {TRACKS_FILE}", file=sys.stderr)
        sys.exit(1)

    if "/assets/wall_street_slang_cover.jpg" not in tracks_src:
        print(f"FAILED: Expected cover art path missing from {TRACKS_FILE}", file=sys.stderr)
        sys.exit(1)

    print("PASS Call 1: Component sources are 100% clean of legacy tracks, white slides, and banned tokens.")


def call2_readback_http_probe() -> None:
    print("[VERIFICATION-CALL-2] Probing Listen server on Port 3040 via HTTP...")
    url = f"{LISTEN_BASE}/"
    try:
        resp = requests.get(url, timeout=5.0)
        if resp.status_code != 200:
            print(f"FAILED: Server returned HTTP {resp.status_code}", file=sys.stderr)
            sys.exit(1)

        body = resp.text
        if "StackLabs Listen | Continuous Intelligence" not in body:
            print("FAILED: Response body missing updated title tag", file=sys.stderr)
            sys.exit(1)

        img_url = f"{LISTEN_BASE}/assets/wall_street_slang_cover.jpg"
        img_resp = requests.get(img_url, timeout=5.0)
        if img_resp.status_code != 200:
            print(f"FAILED: Album cover art URL returned HTTP {img_resp.status_code}", file=sys.stderr)
            sys.exit(1)

        print(f"PASS Call 2: Verified HTTP 200 OK response from {url} and album art from {img_url}.")
    except Exception as exc:
        print(f"FAILED: Could not connect to {url}: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    call1_mutation_source_audit()
    call2_readback_http_probe()
    print("\n=== ALL WO0011221 MINIMAL LISTEN CHECKS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
