#!/usr/bin/env python3
"""
Sovereign OS: KI-070 Anti-Mock Pre-Commit Static Assertion Hook
Path: /home/james/stacklabs/scripts/hooks/pre_commit_ki070_anti_mock.py

Enforces KI-070 (Wet Toothbrush Invariant):
Strictly prevents committing mock box scores, fake telemetry arrays, or
static demo fixtures into the repository metal.
"""

import sys
import os
import re
import subprocess
from typing import List, Tuple, Dict, Any, Optional

PROHIBITED_PATTERNS = [
    ("mock_box_score", re.compile(r'\bmock_box_score\b', re.IGNORECASE)),
    ("fake_telemetry", re.compile(r'\bfake_telemetry\b', re.IGNORECASE)),
    ("static_demo_array", re.compile(r'\bstatic_demo_array\b', re.IGNORECASE)),
    ("mock_game_pk", re.compile(r'\bmock_game_pk\b', re.IGNORECASE)),
    ("DEFAULT_AWAY='HOU'", re.compile(r'DEFAULT_AWAY\s*=\s*[\'"]HOU[\'"]', re.IGNORECASE)),
    ("TODO_replace_mock_before_demo", re.compile(r'(?://|#)\s*TODO:?\s*replace\s+mock\s+before\s+demo', re.IGNORECASE)),
]

TARGET_EXTENSIONS = ('.ts', '.tsx', '.py', '.js', '.jsx', '.mjs', '.cjs')
EXCLUDED_FILES = (
    'pre_commit_ki070_anti_mock.py',
    'test_pre_commit_ki070_anti_mock.py',
)


def scan_text(text: str, filename: str = "<stdin>") -> List[Dict[str, Any]]:
    """Scan given text lines for prohibited mock patterns."""
    violations = []
    for line_idx, line in enumerate(text.splitlines(), start=1):
        for name, regex in PROHIBITED_PATTERNS:
            if regex.search(line):
                violations.append({
                    "file": filename,
                    "line_number": line_idx,
                    "line_content": line.strip(),
                    "pattern": name
                })
    return violations


def scan_staged_diff() -> List[Dict[str, Any]]:
    """Inspect git staged changes for prohibited mock patterns."""
    # 1. Get staged filenames
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        staged_files = [f.strip() for f in proc.stdout.splitlines() if f.strip()]
    except Exception as e:
        print(f"[WARN] Failed to inspect git staged files: {e}", file=sys.stderr)
        return []

    target_files = [
        f for f in staged_files
        if f.endswith(TARGET_EXTENSIONS) and not any(f.endswith(ex) for ex in EXCLUDED_FILES)
    ]

    if not target_files:
        return []

    violations = []
    for f in target_files:
        try:
            diff_proc = subprocess.run(
                ["git", "diff", "--cached", "-U0", "--", f],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            for line in diff_proc.stdout.splitlines():
                # Only check added lines (+), not the +++ file headers
                if line.startswith('+') and not line.startswith('+++'):
                    added_line = line[1:]
                    for name, regex in PROHIBITED_PATTERNS:
                        if regex.search(added_line):
                            violations.append({
                                "file": f,
                                "line_number": "?",
                                "line_content": added_line.strip(),
                                "pattern": name
                            })
        except Exception as e:
            print(f"[WARN] Failed to diff file {f}: {e}", file=sys.stderr)

    return violations


def print_violations_and_abort(violations: List[Dict[str, Any]]) -> None:
    """Print the static assertion failure banner and exit code 1."""
    print("=" * 80, file=sys.stderr)
    print("🛑 STATIC_ASSERT_FAILED: KI-070 Wet Toothbrush Invariant Violated", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(f"Detected {len(violations)} prohibited mock / fake pattern(s) in staged changes:\n", file=sys.stderr)
    for v in violations:
        print(f"  • File:    {v['file']}", file=sys.stderr)
        print(f"    Pattern: {v['pattern']}", file=sys.stderr)
        print(f"    Line:    {v['line_content']}", file=sys.stderr)
        print("-" * 80, file=sys.stderr)
    print("The Pilot's Wet Toothbrush Invariant (KI-070) strictly prohibits committing", file=sys.stderr)
    print("mock box scores, fake telemetry streams, or placeholder demo fixtures.", file=sys.stderr)
    print("Eradicate mock data and connect verified live data sources before committing to metal.", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    sys.exit(1)


def main():
    # Direct test or stdin argument support
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("--help", "-h"):
            print("Usage: pre_commit_ki070_anti_mock.py [--test <string> | <test_string> | --stdin]")
            sys.exit(0)
        elif arg == "--test" and len(sys.argv) > 2:
            test_content = sys.argv[2]
            violations = scan_text(test_content, filename="<cli_test>")
            if violations:
                print_violations_and_abort(violations)
            print("[PASS] KI-070 Anti-Mock assertion passed. Zero mock patterns detected.")
            sys.exit(0)
        elif arg == "--stdin":
            test_content = sys.stdin.read()
            violations = scan_text(test_content, filename="<stdin>")
            if violations:
                print_violations_and_abort(violations)
            print("[PASS] KI-070 Anti-Mock assertion passed. Zero mock patterns detected.")
            sys.exit(0)
        elif not arg.startswith("-"):
            # Direct string argument passed
            test_content = " ".join(sys.argv[1:])
            violations = scan_text(test_content, filename="<cli_arg>")
            if violations:
                print_violations_and_abort(violations)
            print("[PASS] KI-070 Anti-Mock assertion passed. Zero mock patterns detected.")
            sys.exit(0)

    # Git Hook Mode: Scan git staged diffs
    violations = scan_staged_diff()
    if violations:
        print_violations_and_abort(violations)

    print("[PASS] KI-070 Anti-Mock check: Clean. Metal is uncompromised.")
    sys.exit(0)


if __name__ == "__main__":
    main()
