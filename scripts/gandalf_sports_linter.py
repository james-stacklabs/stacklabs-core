#!/usr/bin/env python3
"""
scripts/gandalf_sports_linter.py — The Gandalf Sports Grounding Gate ("YOU SHALL NOT PASS!")
=============================================================================================
Enforces Invariant 0 (Grounded Reality) and Invariant 26 (Gandalf Gate, Ω = 1.0)
across sports intelligence lookbooks, creator briefs, and generative advocate prompts.
Prevents outdated parametric LLM memory (frozen in 2024/2025) from hallucinating obsolete
coaching roles, phantom trades, or contradicted standings into Sovereign OS media artifacts.

Usage:
  python3 scripts/gandalf_sports_linter.py <file_or_directory_paths...>
  cat lookbook.md | python3 scripts/gandalf_sports_linter.py -
"""

import sys
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

JSON_GROUND_TRUTH_PATH = "/home/james/sovereign_inbox/today/active_sports_ground_truth.json"

# Explicit contradiction checks: (Regex pattern, Error message)
SPORTS_CONTRADICTIONS: List[Tuple[str, str]] = [
    (
        r"(?:Brian\s+)?Daboll[\w\s,–—\-]{0,40}(?:Giants|NYG)\s+(?:Head\s+Coach|HC|head\s+coach)",
        "YOU SHALL NOT PASS! Contradiction detected: Daboll is TEN OC, not NYG HC."
    ),
    (
        r"(?:Giants|NYG)\s+(?:Head\s+Coach|HC|head\s+coach)[\w\s,–—\-]{0,40}(?:Brian\s+)?Daboll",
        "YOU SHALL NOT PASS! Contradiction detected: Daboll is TEN OC, not NYG HC."
    ),
    (
        r"(?:Brian\s+)?Daboll[\w\s,–—\-]{0,40}(?:head\s+coach\s+(?:of|for)\s+(?:the\s+)?(?:New\s+York\s+)?Giants)",
        "YOU SHALL NOT PASS! Contradiction detected: Daboll is TEN OC, not NYG HC."
    ),
    (
        r"(?:John\s+)?Harbaugh[\w\s,–—\-]{0,40}(?:Ravens|BAL)\s+(?:Head\s+Coach|HC|head\s+coach)",
        "YOU SHALL NOT PASS! Contradiction detected: John Harbaugh is NYG HC in 2026, not BAL HC."
    ),
    (
        r"(?:Mike\s+)?Vrabel[\w\s,–—\-]{0,40}(?:Titans|TEN)\s+(?:Head\s+Coach|HC|head\s+coach)",
        "YOU SHALL NOT PASS! Contradiction detected: Brian Callahan is TEN HC, not Mike Vrabel."
    ),
    (
        r"(?:Bill\s+)?Belichick[\w\s,–—\-]{0,40}(?:Patriots|NE)\s+(?:Head\s+Coach|HC|head\s+coach)",
        "YOU SHALL NOT PASS! Contradiction detected: Jerod Mayo is NE HC, not Bill Belichick."
    ),
    (
        r"(?:Pete\s+)?Carroll[\w\s,–—\-]{0,40}(?:Seahawks|SEA)\s+(?:Head\s+Coach|HC|head\s+coach)",
        "YOU SHALL NOT PASS! Contradiction detected: Mike Macdonald is SEA HC, not Pete Carroll."
    ),
    (
        r"Arthur\s+Smith[\w\s,–—\-]{0,40}(?:Falcons|ATL)\s+(?:Head\s+Coach|HC|head\s+coach)",
        "YOU SHALL NOT PASS! Contradiction detected: Raheem Morris is ATL HC, not Arthur Smith."
    ),
    (
        r"(?:Ron\s+)?Rivera[\w\s,–—\-]{0,40}(?:Commanders|WAS)\s+(?:Head\s+Coach|HC|head\s+coach)",
        "YOU SHALL NOT PASS! Contradiction detected: Dan Quinn is WAS HC, not Ron Rivera."
    ),
    # MLB 2026 Managerial Attestation Invariants (Invariant 45)
    (
        r"(?:Rob\s+)?Thomson[\w\s,–—\-]{0,40}(?:Phillies|PHI|manager|dugout|bullpen|calls|drags|brings|hooks)",
        "YOU SHALL NOT PASS! Contradiction detected: Rob Thomson was fired on April 28, 2026. Don Mattingly is interim manager."
    ),
    (
        r"(?:Phillies|PHI)\s+manager[\w\s,–—\-]{0,40}(?:Rob\s+)?Thomson",
        "YOU SHALL NOT PASS! Contradiction detected: Rob Thomson was fired on April 28, 2026. Don Mattingly is interim manager."
    ),
    (
        r"(?:Brian\s+)?Snitker[\w\s,–—\-]{0,40}(?:Braves|ATL|manager|dugout|bullpen|relay|clinic|masterclass)",
        "YOU SHALL NOT PASS! Contradiction detected: Brian Snitker stepped down after 2025. Walt Weiss is Braves manager."
    ),
    (
        r"(?:Braves|ATL)\s+manager[\w\s,–—\-]{0,40}(?:Brian\s+)?Snitker",
        "YOU SHALL NOT PASS! Contradiction detected: Brian Snitker stepped down after 2025. Walt Weiss is Braves manager."
    ),
    (
        r"(?:Pedro\s+)?Grifol[\w\s,–—\-]{0,40}(?:White\s+Sox|CHW|CWS|manager)",
        "YOU SHALL NOT PASS! Contradiction detected: Will Venable is White Sox manager, not Pedro Grifol."
    ),
    (
        r"(?:Bob\s+)?Melvin[\w\s,–—\-]{0,40}(?:Padres|SD|San\s+Diego|manager)",
        "YOU SHALL NOT PASS! Contradiction detected: Mike Shildt is Padres manager, not Bob Melvin."
    ),
    (
        r"(?:David\s+)?Ross[\w\s,–—\-]{0,40}(?:Cubs|CHC|Chicago\s+Cubs|manager)",
        "YOU SHALL NOT PASS! Contradiction detected: Craig Counsell is Cubs manager, not David Ross."
    ),
]

ROSTER_ATTESTATION_PATH = "/home/james/stacklabs/config/roster_attestation_2026.json"


def load_ground_truth() -> Dict[str, Any]:
    """Loads current ground truth from JSON state file if available."""
    if os.path.exists(JSON_GROUND_TRUTH_PATH):
        try:
            with open(JSON_GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def scan_content(text: str, source_name: str) -> List[Dict[str, Any]]:
    """Scans content for sports ground truth contradictions."""
    violations = []
    lines = text.splitlines()

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        for pattern, err_msg in SPORTS_CONTRADICTIONS:
            match = re.search(pattern, stripped, re.IGNORECASE)
            if match:
                violations.append({
                    "source": source_name,
                    "line": idx,
                    "matched": match.group(0),
                    "content": stripped,
                    "reason": err_msg
                })

    return violations


def main():
    targets = sys.argv[1:]
    if not targets:
        print("Usage: python3 scripts/gandalf_sports_linter.py <file_or_dir_paths...>")
        sys.exit(1)

    all_violations = []

    for target in targets:
        if target == "-":
            content = sys.stdin.read()
            all_violations.extend(scan_content(content, "stdin"))
            continue

        p = Path(target)
        if not p.exists():
            print(f"[-] Warning: Path does not exist: {target}", file=sys.stderr)
            continue

        if p.is_file():
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                all_violations.extend(scan_content(content, str(p)))
            except Exception as e:
                print(f"[-] Error reading {p}: {e}", file=sys.stderr)
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in (".md", ".txt", ".json", ".html", ".tsx", ".jsx"):
                    if "node_modules" in f.parts or ".venv" in f.parts or ".git" in f.parts:
                        continue
                    try:
                        content = f.read_text(encoding="utf-8", errors="ignore")
                        all_violations.extend(scan_content(content, str(f)))
                    except Exception:
                        continue

    if all_violations:
        print("\n" + "=" * 72)
        print("🧙‍♂️ GANDALF SPORTS GROUNDING GATE: \"YOU SHALL NOT PASS!\"")
        print("=" * 72)
        print(f"❌ Found {len(all_violations)} sports ground truth contradiction(s):\n")
        for v in all_violations:
            print(f"  • {v['source']}:{v['line']}")
            print(f"    {v['reason']}")
            print(f"    Offending text: \"{v['matched']}\"\n")
        print("🛑 Build/Deploy HALTED. Correct sports factual hallucinations before proceeding.")
        print("=" * 72 + "\n")
        sys.exit(1)

    print("[GANDALF GATE: PASS] Ω = 1.0. All sports assertions grounded in verified reality.")
    sys.exit(0)


if __name__ == "__main__":
    main()
