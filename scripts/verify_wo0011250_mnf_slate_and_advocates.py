#!/home/james/stacklabs/.venv/bin/python3
"""
Verification Suite for WO0011250: MNF Slate Ribbon Priority, Schedule Ingestion, and Advocate Roster Refresh
Path: /home/james/stacklabs/scripts/verify_wo0011250_mnf_slate_and_advocates.py
Author: James Carroll (Pilot) & Lead Systems Architect
"""
import json
import os
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
DB_PATH = REPO_ROOT / "dna" / "sovereign_now.db"
FAAS_PORT = int(os.environ.get("FAAS_PORT", "3033"))
SCHEDULE_URL = f"http://127.0.0.1:{FAAS_PORT}/api/schedule"

FORBIDDEN_OCD_TOKENS = [
    "touches wood",
    "covers eyes",
    "behind the sofa",
    "closes eyes",
]

EXPECTED_HANDLES = {
    "@BarfFanStack",
    "@burl_bayou",
    "@SammyBoySmith_The_Savant",
    "@shanahan_21_personnel_ptsd",
    "@burgundy_gold_scar_tissue",
}


def verify_api_slate_sorting() -> None:
    print(f"[1/4] Probing {SCHEDULE_URL} for MNF slate priority sorting...")
    req = urllib.request.Request(SCHEDULE_URL, headers={"User-Agent": "StackLabs-Verifier/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"Expected HTTP 200, got {resp.status}"
        games = json.loads(resp.read().decode("utf-8"))

    assert isinstance(games, list) and len(games) > 0, "Expected non-empty games list from /api/schedule"

    mnf_idx = None
    first_final_nfl_idx = None
    for idx, g in enumerate(games):
        away_code = (g.get("away_team", {}) or {}).get("code") or g.get("awayTeam")
        home_code = (g.get("home_team", {}) or {}).get("code") or g.get("homeTeam")
        status = g.get("status", "")
        sport = g.get("sport", "")
        if away_code == "WSH" and home_code == "SF":
            mnf_idx = idx
            mnf_status = status
        if sport == "nfl" and status == "FINAL" and first_final_nfl_idx is None:
            first_final_nfl_idx = idx

    assert mnf_idx is not None, "WSH @ SF not found in /api/schedule response!"
    assert mnf_status in ("SCHEDULED", "LIVE", "WARMUP"), f"Unexpected status for WSH @ SF: {mnf_status}"
    if first_final_nfl_idx is not None:
        assert mnf_idx < first_final_nfl_idx, (
            f"Sorting defect: WSH @ SF (idx={mnf_idx}, status={mnf_status}) appeared AFTER "
            f"first FINAL NFL game (idx={first_final_nfl_idx})!"
        )
    print(f"  ✅ PASS: WSH @ SF is at index {mnf_idx} (status={mnf_status}) ahead of FINAL NFL games (first_final_idx={first_final_nfl_idx}).")


def verify_frontend_build() -> None:
    print("[2/4] Verifying apps/faas production build & SlateSwitcherRibbon.tsx...")
    ribbon_path = REPO_ROOT / "apps" / "faas" / "src" / "components" / "SlateSwitcherRibbon.tsx"
    content = ribbon_path.read_text(encoding="utf-8")
    assert "getStatusPriority" in content, "getStatusPriority missing from SlateSwitcherRibbon.tsx"
    res = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(REPO_ROOT / "apps" / "faas"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, f"Frontend build failed:\n{res.stdout}\n{res.stderr}"
    print("  ✅ PASS: apps/faas compiled cleanly with zero TypeScript errors.")


def verify_systemd_timer() -> None:
    print("[3/4] Verifying faas_polysport_slate_sync.timer status...")
    res = subprocess.run(
        ["systemctl", "--user", "is-active", "faas_polysport_slate_sync.timer"],
        capture_output=True,
        text=True,
        check=False,
    )
    state = res.stdout.strip()
    assert state == "active", f"Expected timer state 'active', got '{state}'"
    print("  ✅ PASS: faas_polysport_slate_sync.timer is active.")


def verify_advocate_anti_ocd() -> None:
    print(f"[4/4] Auditing 5 MNF advocate profiles in {DB_PATH}...")
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        "SELECT handle, name, team, bio, triggers, anti_patterns FROM fanstack_advocates WHERE handle IN (?, ?, ?, ?, ?)",
        tuple(EXPECTED_HANDLES),
    )
    rows = cur.fetchall()
    conn.close()

    found_handles = {r[0] for r in rows}
    missing = EXPECTED_HANDLES - found_handles
    assert not missing, f"Missing expected advocates in fanstack_advocates: {missing}"

    for handle, name, team, bio, triggers, anti_patterns in rows:
        combined = f"{bio} {triggers}".lower()
        for token in FORBIDDEN_OCD_TOKENS:
            assert token not in combined, f"Forbidden OCD token '{token}' found in {handle}"
        print(f"  ✅ Verified {handle} ({name} • {team}) — zero OCD tokens.")


def main() -> int:
    verify_api_slate_sorting()
    verify_frontend_build()
    verify_systemd_timer()
    verify_advocate_anti_ocd()
    print("\n🎯 ALL WO0011250 VERIFICATION CHECKS PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
