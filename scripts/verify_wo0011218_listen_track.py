#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Verification Suite for WO0011218: Deploy Decoding Slang to Listen Portal
Path: /home/james/stacklabs/scripts/verify_wo0011218_listen_track.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
Host: Clio (clio / Dedicated Linux Host / 100.96.77.20)
Governing Standards: Invariant 15 (Two-Call Mandate), 32 (Law of "I"), 35 (.venv), 50
"""

import sys
from pathlib import Path

import requests

REPO_ROOT = Path("/home/james/stacklabs")
AUDIO_FILE = REPO_ROOT / "apps" / "listen" / "public" / "audio" / "Decoding_Slang_to_Beat_Wall_Street.m4a"
TRACKS_FILE = REPO_ROOT / "apps" / "listen" / "src" / "data" / "tracks.ts"
LISTEN_BASE = "http://127.0.0.1:3040"


def verification_call1_mutation_check() -> None:
    print("[VERIFICATION-CALL-1] Checking disk artifacts and tracks.ts registration...")
    if not AUDIO_FILE.exists():
        print(f"FAILED: Audio file {AUDIO_FILE} does not exist.", file=sys.stderr)
        sys.exit(1)

    file_size = AUDIO_FILE.stat().st_size
    if file_size < 30_000_000:
        print(f"FAILED: Audio file size {file_size} is suspiciously small.", file=sys.stderr)
        sys.exit(1)

    tracks_content = TRACKS_FILE.read_text(encoding="utf-8")
    if "decoding-slang-to-beat-wall-street-19m" not in tracks_content:
        print("FAILED: Track ID not found in tracks.ts.", file=sys.stderr)
        sys.exit(1)

    if "/audio/Decoding_Slang_to_Beat_Wall_Street.m4a" not in tracks_content:
        print("FAILED: Audio source path not found in tracks.ts.", file=sys.stderr)
        sys.exit(1)

    print(f"PASS Call 1: Audio file verified ({file_size} bytes) and registered in tracks.ts.")


def verification_call2_readback_check() -> None:
    print("[VERIFICATION-CALL-2] Probing Listen server on Port 3040 via HTTP...")
    root_url = f"{LISTEN_BASE}/"
    audio_url = f"{LISTEN_BASE}/audio/Decoding_Slang_to_Beat_Wall_Street.m4a"

    try:
        r_root = requests.get(root_url, timeout=5.0)
        if r_root.status_code != 200:
            print(f"FAILED: Root {root_url} returned HTTP {r_root.status_code}", file=sys.stderr)
            sys.exit(1)

        r_audio = requests.head(audio_url, timeout=5.0)
        if r_audio.status_code != 200:
            print(f"FAILED: Audio endpoint {audio_url} returned HTTP {r_audio.status_code}", file=sys.stderr)
            sys.exit(1)

        print(f"PASS Call 2: Verified HTTP 200 OK on both {root_url} and {audio_url}.")
    except Exception as exc:
        print(f"FAILED: Connection error to {LISTEN_BASE}: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    verification_call1_mutation_check()
    verification_call2_readback_check()
    print("\n=== ALL WO0011218 LISTEN MOUNT CHECKS PASSED ===")


if __name__ == "__main__":
    main()
