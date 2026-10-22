#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Register 'Decoding Slang to Beat Wall Street' Track in Listen Portal
Path: /home/james/stacklabs/scripts/register_listen_slang_track.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
Host: Clio (clio / Dedicated Linux Host / 100.96.77.20)
Governing Standards: Invariant 15, 32 (Law of "I"), 35 (.venv), 50
"""

import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
SOURCE_AUDIO = REPO_ROOT / "pilot_drops" / "downloads" / "scratch" / "Decoding_Slang_to_Beat_Wall_Street.m4a"
BACKUP_SOURCE = REPO_ROOT / "pilot_drops" / "archives" / "20261017_podcasts" / "Decoding_Slang_to_Beat_Wall_Street.m4a"
TARGET_AUDIO_DIR = REPO_ROOT / "apps" / "listen" / "public" / "audio"
TARGET_AUDIO = TARGET_AUDIO_DIR / "Decoding_Slang_to_Beat_Wall_Street.m4a"
TRACKS_FILE = REPO_ROOT / "apps" / "listen" / "src" / "data" / "tracks.ts"

NEW_TRACK_CODE = """  {
    id: 'decoding-slang-to-beat-wall-street-19m',
    title: "Decoding Internet Slang to Beat Wall Street Algorithms [19-Min Deep Dive]",
    shortTitle: "Decoding Slang vs Wall Street",
    subtitle: "19:10 Executive Master Deep Dive • The Mustard & Golf Balls Paradox, Static NLP Failure & The 400ms Polymorphic Bridge",
    audioSrc: "/audio/Decoding_Slang_to_Beat_Wall_Street.m4a",
    coverArt: "/assets/latency_fabric_cover.png",
    durationSeconds: 1151,
    chapters: [
      { id: 'slang-c1', number: '01', title: "The Mustard & Golf Balls Paradox: Wall Street's Blind Spot", timestamp: '00:00', seconds: 0 },
      { id: 'slang-c2', number: '02', title: "Two Fatal Failure Modes: 100% Data Drop vs Literal Hallucination", timestamp: '01:32', seconds: 92 },
      { id: 'slang-c3', number: '03', title: "The 4-Step Continuous Intelligence Architecture (400ms Loop)", timestamp: '03:55', seconds: 235 },
      { id: 'slang-c4', number: '04', title: "Adversarial Signaling: Gamma Ramps, Emojis & Bleacher Revolts", timestamp: '06:30', seconds: 390 },
      { id: 'slang-c5', number: '05', title: "Kinetic Action: Tennessee Mustard Artillery & The Florida Cleat", timestamp: '08:20', seconds: 500 },
      { id: 'slang-c6', number: '06', title: "Subcultural Evasion: BYU Soaking/Quaking & The Michigan Vacuum Manifesto", timestamp: '10:20', seconds: 620 },
      { id: 'slang-c7', number: '07', title: "Fan Psychology: SurlyHorns Polecat & Alabama Pawl Finebaum", timestamp: '12:50', seconds: 770 },
      { id: 'slang-c8', number: '08', title: "The Polymorphic Bridge: Small-Ball Silicon Outpacing Cloud Giants", timestamp: '16:30', seconds: 990 },
    ],
  },
"""


def deploy_audio_asset() -> None:
    src = SOURCE_AUDIO if SOURCE_AUDIO.exists() else BACKUP_SOURCE
    if not src.exists():
        print(f"ERROR: Audio source not found at {SOURCE_AUDIO} or {BACKUP_SOURCE}", file=sys.stderr)
        sys.exit(1)

    TARGET_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    if not TARGET_AUDIO.exists() or TARGET_AUDIO.stat().st_size != src.stat().st_size:
        print(f"Deploying audio asset {src.name} to {TARGET_AUDIO}...")
        shutil.copy2(src, TARGET_AUDIO)
        print(f"Copied {TARGET_AUDIO.stat().st_size} bytes successfully.")
    else:
        print(f"Audio asset {TARGET_AUDIO} already in place ({TARGET_AUDIO.stat().st_size} bytes).")


def mount_track_in_tracks_ts() -> None:
    if not TRACKS_FILE.exists():
        print(f"ERROR: {TRACKS_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    content = TRACKS_FILE.read_text(encoding="utf-8")
    if "decoding-slang-to-beat-wall-street-19m" in content:
        print("OK: Track already registered in tracks.ts.")
        return

    marker = "export const TRACKS: Track[] = [\n"
    if marker not in content:
        print(f"ERROR: Marker '{marker.strip()}' not found in {TRACKS_FILE}", file=sys.stderr)
        sys.exit(1)

    idx = content.find(marker) + len(marker)
    updated = content[:idx] + NEW_TRACK_CODE + content[idx:]
    TRACKS_FILE.write_text(updated, encoding="utf-8")
    print(f"SUCCESS: Prepend track to {TRACKS_FILE}.")


def main() -> None:
    deploy_audio_asset()
    mount_track_in_tracks_ts()


if __name__ == "__main__":
    main()
