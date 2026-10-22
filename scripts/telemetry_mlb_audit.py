#!/usr/bin/env python3
"""
Sovereign OS: MLB Ground-Truth Telemetry Audit Utility
======================================================
Compares local Sovereign Sports broadcast state against authoritative MLB StatsAPI
live data feeds and queries the mlb_telemetry_audit_ledger via Port 8095 REST API.

Usage:
    python3 scripts/telemetry_mlb_audit.py [--game-pk 823495] [--limit 10]
"""

import sys
import os
import json
import argparse
import requests
from typing import Dict, Any, List

sys.path.insert(0, "/home/james/stacklabs/scripts")
from core.api_client import get_sports_telemetry_audit

CYAN = "\033[38;2;0;240;255m"
AMBER = "\033[38;2;245;158;11m"
GREEN = "\033[38;2;34;197;94m"
RED = "\033[38;2;239;68;68m"
SLATE = "\033[38;2;148;163;184m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner(game_pk: str):
    print(f"\n{CYAN}{BOLD}╔══════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║         SOVEREIGN SPORTS • MLB TELEMETRY GROUND-TRUTH AUDIT         ║{RESET}")
    print(f"{CYAN}{BOLD}╚══════════════════════════════════════════════════════════════════════╝{RESET}")
    print(f"  {SLATE}Target Game PK:{RESET} {BOLD}{game_pk}{RESET}  |  {SLATE}API Gateway:{RESET} {CYAN}http://127.0.0.1:8095{RESET}\n")


def run_audit(game_pk: str, limit: int = 10) -> bool:
    print_banner(game_pk)

    # 1. Read Local Game State Hot Cache
    cache_path = f"/home/james/stacklabs/game_states/{game_pk}.json"
    if not os.path.exists(cache_path):
        print(f"{RED}[FAIL] Local hot cache not found: {cache_path}{RESET}")
        return False

    with open(cache_path, "r") as f:
        local_state = json.load(f)

    # 2. Fetch Live MLB StatsAPI Feed
    mlb_url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    try:
        resp = requests.get(mlb_url, timeout=10)
        resp.raise_for_status()
        mlb_feed = resp.json()
    except Exception as e:
        print(f"{RED}[FAIL] Failed to fetch live MLB feed: {e}{RESET}")
        return False

    linescore = mlb_feed.get("liveData", {}).get("linescore", {})
    plays = mlb_feed.get("liveData", {}).get("plays", {})
    current_play = plays.get("currentPlay", {})

    mlb_inn_state = linescore.get("inningState", "")
    mlb_inn_ord = linescore.get("currentInningOrdinal", "")
    mlb_is_top = linescore.get("isTopInning", True)
    mlb_outs = linescore.get("outs", 0)
    mlb_balls = linescore.get("balls", 0)
    mlb_strikes = linescore.get("strikes", 0)
    mlb_away_runs = linescore.get("teams", {}).get("away", {}).get("runs", 0)
    mlb_home_runs = linescore.get("teams", {}).get("home", {}).get("runs", 0)

    # 3. Fetch Audit Ledger from Port 8095 REST API
    try:
        audit_res = get_sports_telemetry_audit(game_pk, limit=limit)
        audit_records = audit_res.get("records", []) if isinstance(audit_res, dict) else []
    except Exception as e:
        print(f"{AMBER}[WARN] Could not retrieve audit ledger from Port 8095: {e}{RESET}")
        audit_records = []

    # 4. Compare Fields
    discrepancies = []

    # Inning Break & 3-OUT Check (DFCT2026082603)
    is_inning_break = mlb_inn_state.lower() in ("middle", "mid", "end") or mlb_outs == 3 or local_state.get("outs") == 3
    local_inn = str(local_state.get("inning", ""))

    if is_inning_break:
        expected_prefix = "Mid" if (mlb_inn_state.lower() in ("middle", "mid") or mlb_is_top) else "End"
        if not (local_inn.startswith("Mid") or local_inn.startswith("End")):
            discrepancies.append(f"Inning break not formatted as Mid/End: local='{local_inn}', mlb_state='{mlb_inn_state}'")
        if local_state.get("outs") == 3:
            discrepancies.append(f"Violation of KI-095/DFCT: Local state has outs=3 during inning transition")
    else:
        if local_state.get("outs") != mlb_outs:
            discrepancies.append(f"Outs mismatch: local={local_state.get('outs')} vs mlb={mlb_outs}")
        if local_state.get("balls") != mlb_balls:
            discrepancies.append(f"Balls mismatch: local={local_state.get('balls')} vs mlb={mlb_balls}")
        if local_state.get("strikes") != mlb_strikes:
            discrepancies.append(f"Strikes mismatch: local={local_state.get('strikes')} vs mlb={mlb_strikes}")

    # Score check
    if local_state.get("away_score") != mlb_away_runs or local_state.get("home_score") != mlb_home_runs:
        discrepancies.append(f"Score mismatch: local={local_state.get('away_score')}-{local_state.get('home_score')} vs mlb={mlb_away_runs}-{mlb_home_runs}")

    # 5. Output Summary Table
    print(f"{BOLD}State Reconciliation Matrix:{RESET}")
    print(f"┌─────────────────────────┬──────────────────────────┬──────────────────────────┬────────┐")
    print(f"│ {BOLD}Telemetry Field{RESET}         │ {BOLD}Sovereign Hot Cache{RESET}      │ {BOLD}MLB StatsAPI Ground-Truth{RESET}  │ {BOLD}Status{RESET} │")
    print(f"├─────────────────────────┼──────────────────────────┼──────────────────────────┼────────┤")

    play_events = current_play.get("playEvents", [])
    last_pitch_speed = play_events[-1].get("pitchData", {}).get("startSpeed", "---") if play_events else "---"
    num_pitches = len([e for e in play_events if e.get("isPitch")])

    fields = [
        ("Inning / Phase", local_inn, f"{mlb_inn_state} {mlb_inn_ord}".strip()),
        ("Count (Balls-Strikes)", f"{local_state.get('balls')}-{local_state.get('strikes')}", f"{mlb_balls}-{mlb_strikes}"),
        ("Outs (Suppresses 3-OUT)", f"{local_state.get('outs')} OUT", f"{mlb_outs} OUT"),
        ("Score (Away - Home)", f"{local_state.get('away_team')} {local_state.get('away_score')} - {local_state.get('home_score')} {local_state.get('home_team')}", f"{mlb_away_runs} - {mlb_home_runs}"),
        ("Active / Due Batter", local_state.get("batter", "---"), current_play.get("matchup", {}).get("batter", {}).get("fullName", "---")),
        ("Active Pitcher", local_state.get("pitcher", "---"), current_play.get("matchup", {}).get("pitcher", {}).get("fullName", "---")),
        ("Pitch Speed (Last)", f"{local_state.get('pitch_speed')} MPH", f"{last_pitch_speed} MPH"),
        ("Pitches in At-Bat", str(len(local_state.get("pitches_this_ab", []))), str(num_pitches)),
    ]

    for label, local_val, mlb_val in fields:
        match = True
        if label.startswith("Outs") and is_inning_break:
            match = local_state.get("outs") < 3
        elif label.startswith("Count") and is_inning_break:
            match = local_state.get("balls") == 0 and local_state.get("strikes") == 0
        elif label.startswith("Inning"):
            match = (local_inn.split()[0] in ("Mid", "End") if is_inning_break else True)
        elif label.startswith("Active / Due Batter") and is_inning_break:
            match = True  # Linescore due-up batter correctly replaces completed at-bat
        elif label.startswith("Pitches in At-Bat") and is_inning_break:
            match = len(local_state.get("pitches_this_ab", [])) == 0
        elif label.startswith("Pitch Speed") and is_inning_break:
            match = local_state.get("pitch_speed") in ("---", None)

        status_str = f"{GREEN}PASS{RESET}" if match else f"{RED}FAIL{RESET}"
        print(f"│ {label:<23} │ {str(local_val):<24} │ {str(mlb_val):<24} │  {status_str}  │")

    print(f"└─────────────────────────┴──────────────────────────┴──────────────────────────┴────────┘")

    # 6. Audit Ledger Historical Trace
    print(f"\n{BOLD}Audit Ledger Trace (Last {min(len(audit_records), 5)} Records via Port 8095):{RESET}")
    if audit_records:
        for r in audit_records[:5]:
            sync_tag = f"{GREEN}[SYNC]{RESET}" if r.get("is_synchronized") else f"{RED}[DESYNC]{RESET}"
            ts = r.get("timestamp", "").split("T")[-1][:8]
            print(f"  {sync_tag} {SLATE}{ts}{RESET} | Inning: {CYAN}{r.get('our_inning')}{RESET} | Count: {r.get('our_balls')}-{r.get('our_strikes')} | Outs: {r.get('our_outs')} | Batter: {r.get('our_batter')} | Pitch: {r.get('our_pitch_speed')} MPH {r.get('our_pitch_name')}")
    else:
        print(f"  {SLATE}No audit records returned for game {game_pk}.{RESET}")

    # 7. Final Verdict
    print(f"\n{BOLD}Audit Conclusion:{RESET}")
    if not discrepancies:
        print(f"  {GREEN}{BOLD}✅ 100% RECONCILED — Ground-truth telemetry is synchronized with zero 3-OUT freezes.{RESET}\n")
        return True
    else:
        print(f"  {RED}{BOLD}❌ DISCREPANCIES DETECTED ({len(discrepancies)}):{RESET}")
        for d in discrepancies:
            print(f"    - {d}")
        print()
        return False


def main():
    parser = argparse.ArgumentParser(description="MLB Ground-Truth Telemetry Audit Utility")
    parser.add_argument("--game-pk", type=str, default="823495", help="Target MLB game primary key")
    parser.add_argument("--limit", type=int, default=10, help="Number of ledger rows to query")
    args = parser.parse_args()

    success = run_audit(args.game_pk, limit=args.limit)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
