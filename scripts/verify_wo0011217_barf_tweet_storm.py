#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Verification Suite for WO0011217: Dynamic @BarfFanStack Discord Burst Synthesizer
Path: /home/james/stacklabs/scripts/verify_wo0011217_barf_tweet_storm.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
Host: Clio (clio / Dedicated Linux Host / 100.96.77.20)
Active Gemini Model Invariant: gemini-3.8-flash (Strict October 2026 Production Standard)
Governing Standards: Invariant 0, 15 (Two-Call Mandate), 32 (Law of "I"), 35 (.venv), 50
"""

import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path("/home/james/stacklabs")
DB_PATH = REPO_ROOT / "data" / "morning_wiretap.db"
VFS_STORM_PATH = Path("/dev/shm/vfs/telemetry/barf_latest_tweet_storm.json")
FAAS_API_BASE = "http://127.0.0.1:3033"


def call1_verify_synthesizer_cli() -> None:
    print("[TEST-CALL-1] Executing barf_discord_burst_tweet_synthesizer.py...")
    cmd = [
        str(REPO_ROOT / ".venv" / "bin" / "python3"),
        str(REPO_ROOT / "scripts" / "barf_discord_burst_tweet_synthesizer.py"),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if res.returncode != 0:
        print(f"FAILED: Synthesizer exited with {res.returncode}:\n{res.stderr}", file=sys.stderr)
        sys.exit(1)
    print("PASS Call 1: Synthesizer CLI executed cleanly.")


def call2_verify_vfs_and_sqlite() -> None:
    print("[TEST-CALL-2] Reading back VFS artifact and SQLite records...")
    if not VFS_STORM_PATH.exists():
        print(f"FAILED: VFS artifact {VFS_STORM_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    storm_data = json.loads(VFS_STORM_PATH.read_text(encoding="utf-8"))
    tweets = storm_data.get("tweets", [])
    if len(tweets) != 4:
        print(f"FAILED: Expected 4 verified tweet blocks, got {len(tweets)}.", file=sys.stderr)
        sys.exit(1)

    for tw in tweets:
        clen = tw["char_count"]
        pnum = tw["part_number"]
        txt = tw["text"]
        if clen > 280:
            print(f"FAILED: Tweet {pnum} length {clen} exceeds 280 chars: {txt}", file=sys.stderr)
            sys.exit(1)
        if pnum == 4 and "@TheWardyNYM" not in txt:
            print(f"FAILED: Tweet 4 missing @TheWardyNYM: {txt}", file=sys.stderr)
            sys.exit(1)

    storm_id = storm_data["storm_id"]
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT storm_id, shibboleth_id, z_score FROM barf_tweet_storms WHERE storm_id = ?;", (storm_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        print(f"FAILED: Storm ID {storm_id} not found in barf_tweet_storms table.", file=sys.stderr)
        sys.exit(1)

    print(f"PASS Call 2: Verified 4 tweets <= 280 chars, @TheWardyNYM tag, VFS, and DB record ({row[0]}).")


def call3_verify_api_endpoint() -> None:
    print("[TEST-CALL-3] Probing FastAPI endpoint /api/faas/lexicon/barf_tweet_storm...")
    url = f"{FAAS_API_BASE}/api/faas/lexicon/barf_tweet_storm"
    try:
        resp = requests.get(url, timeout=5.0)
        if resp.status_code != 200:
            print(f"FAILED: Endpoint returned HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
            sys.exit(1)
        data = resp.json()
        if data.get("status") not in ("ONLINE", "STANDBY") or not data.get("storm"):
            print(f"FAILED: Unexpected API response payload: {data}", file=sys.stderr)
            sys.exit(1)
        print(f"PASS Call 3: Verified API returns HTTP 200 with storm {data['storm']['storm_id']}.")
    except Exception as exc:
        print(f"FAILED: Could not connect to {url}: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    call1_verify_synthesizer_cli()
    call2_verify_vfs_and_sqlite()
    call3_verify_api_endpoint()
    print("\n=== ALL WO0011217 DYNAMIC BARF SYNTHESIZER CHECKS PASSED ===")


if __name__ == "__main__":
    main()
