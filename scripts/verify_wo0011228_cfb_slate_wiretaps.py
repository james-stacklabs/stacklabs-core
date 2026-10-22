#!/usr/bin/env python3
"""
StackLabs Two-Call Verification Gate for WO0011228
Path: /home/james/stacklabs/scripts/verify_wo0011228_cfb_slate_wiretaps.py

Verifies:
1. scripts/sync_cfb_top25_ground_truth.py execution and output schema.
2. scripts/compile_ground_truth_markdown.py execution and Section 4 compilation.
3. Independent read-back inspection of ground_truth/sports_ground_truth.json and SPORTS_GROUND_TRUTH_SNAPSHOT.md.
"""

import json
import subprocess
import sys
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")
VENV_PYTHON = STACKLABS_ROOT / ".venv" / "bin" / "python3"
JSON_PATH = STACKLABS_ROOT / "ground_truth" / "sports_ground_truth.json"
MD_PATH = STACKLABS_ROOT / "ground_truth" / "SPORTS_GROUND_TRUTH_SNAPSHOT.md"

def run_cmd(cmd, desc):
    print(f"[EXEC] {desc}...")
    res = subprocess.run([str(VENV_PYTHON)] + cmd, capture_output=True, text=True, cwd=str(STACKLABS_ROOT))
    if res.returncode != 0:
        print(f"[FAIL] {desc} failed (exit {res.returncode}):\n{res.stderr}\n{res.stdout}")
        sys.exit(1)
    print(f"[PASS] {desc} succeeded.")
    return res.stdout

def main():
    print("================================================================================")
    print("🔒 WO0011228 VERIFICATION: CFB TOP 25 SLATE & BLEACHER WIRETAP OPERATIONS")
    print("================================================================================")

    # CALL 1: Synchronize and Compile
    run_cmd(["scripts/sync_cfb_top25_ground_truth.py"], "Call 1A: Ingest VFS Slate & Sync sports_ground_truth.json")
    run_cmd(["scripts/compile_ground_truth_markdown.py"], "Call 1B: Recompile Ground Truth Markdown Snapshots")

    # CALL 2: Independent Read-Back Verification (Two-Call Mandate)
    print("\n[CALL 2] Inspecting disk state directly...")
    
    if not JSON_PATH.exists():
        print(f"[FAIL] Missing {JSON_PATH}")
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    cfb_data = data.get("cfb_top25_slate_20261017")
    if not cfb_data:
        print("[FAIL] Missing 'cfb_top25_slate_20261017' in sports_ground_truth.json")
        sys.exit(1)

    games = cfb_data.get("games", [])
    print(f"[OK] sports_ground_truth.json contains {len(games)} ranked CFB matchups.")
    if len(games) < 15:
        print(f"[FAIL] Expected at least 15 games, found {len(games)}")
        sys.exit(1)

    # Verify ND @ BYU wiretap
    nd_byu = next((g for g in games if "ND" in g["away_team"]["code"] and "BYU" in g["home_team"]["code"]), None)
    if not nd_byu:
        print("[FAIL] Missing ND @ BYU matchup in CFB slate")
        sys.exit(1)
    
    wt = nd_byu.get("wiretap")
    if not wt or "a6kFatjvbNU" not in wt.get("stream_id", ""):
        print(f"[FAIL] ND @ BYU wiretap not resolved to a6kFatjvbNU: {wt}")
        sys.exit(1)
    print(f"[OK] ND @ BYU wiretap verified: {wt.get('stream_id')} ({wt.get('title')})")

    # Inspect Markdown
    if not MD_PATH.exists():
        print(f"[FAIL] Missing {MD_PATH}")
        sys.exit(1)

    md_content = MD_PATH.read_text(encoding="utf-8")
    if "## 4. College Football Week 7 Top 25 Slate & Bleacher Wiretaps" not in md_content:
        print("[FAIL] Missing Section 4 header in SPORTS_GROUND_TRUTH_SNAPSHOT.md")
        sys.exit(1)

    key_tokens = ["Notre Dame", "BYU", "Georgia", "Alabama", "Tennessee", "Miami"]
    for token in key_tokens:
        if token not in md_content:
            print(f"[FAIL] Missing token '{token}' in SPORTS_GROUND_TRUTH_SNAPSHOT.md")
            sys.exit(1)
    print(f"[OK] SPORTS_GROUND_TRUTH_SNAPSHOT.md verified with all key marquee programs.")

    print("\n================================================================================")
    print("✅ WO0011228 VERIFICATION COMPLETE: ALL GATES PASSED")
    print("================================================================================")

if __name__ == "__main__":
    main()
