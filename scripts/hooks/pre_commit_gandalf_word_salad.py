#!/usr/bin/env python3
"""
pre_commit_gandalf_word_salad.py — The Gandalf Pre-Commit Hook ("YOU SHALL NOT PASS!")
======================================================================================
Path: /home/james/stacklabs/scripts/hooks/pre_commit_gandalf_word_salad.py

Enforces Invariant 26 (The Gandalf Invariant):
Strictly intercepts and blocks AI agents from committing internal prompt instructions,
port numbers, or architectural word-salad space fillers into customer-facing frontend UI.
"""

import sys
import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any

PROHIBITED_UI_PATTERNS = [
    ("port_number_in_ui", re.compile(r'\bPORT\s+\d{4,5}\b', re.IGNORECASE)),
    ("zero_chatrooms", re.compile(r'\bZERO\s+CHATROOMS\b', re.IGNORECASE)),
    ("zero_3d_arenas", re.compile(r'\bZERO\s+3D\s+ARENAS\b', re.IGNORECASE)),
    ("clio_forge_metal", re.compile(r'\bCLIO\s+FORGE\s+METAL\b', re.IGNORECASE)),
    ("forge_metal", re.compile(r'\bFORGE\s+METAL\b', re.IGNORECASE)),
    ("invariant_citation", re.compile(r'\bINVARIANT\s+\d+\b', re.IGNORECASE)),
    ("rule_zero_citation", re.compile(r'\bRULE\s+ZERO\b', re.IGNORECASE)),
    ("compliance_guardrail", re.compile(r'\bCOMPLIANCE\s+GUARDRAIL\b', re.IGNORECASE)),
    ("lightweight_info_utility", re.compile(r'\bLIGHTWEIGHT\s+INFO\s+UTILITY\b', re.IGNORECASE)),
    ("prompt_for_filename", re.compile(r'\bPROMPT_FOR_\b', re.IGNORECASE)),
]

TARGET_EXTENSIONS = ('.tsx', '.jsx', '.html', '.vue')
EXCLUDED_PATHS = ('scripts/', 'tests/', '.agents/', 'dna/', 'node_modules/', 'dist/')

def scan_text(text: str, filename: str) -> List[Dict[str, Any]]:
    violations = []
    lines = text.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue
        if stripped.startswith("import ") or stripped.startswith("export type "):
            continue

        for name, regex in PROHIBITED_UI_PATTERNS:
            match = regex.search(line)
            if match:
                violations.append({
                    "file": filename,
                    "line_number": line_idx,
                    "line_content": stripped,
                    "matched": match.group(0),
                    "pattern": name
                })
    return violations

def check_zero_ports():
    linter_path = Path(__file__).resolve().parent.parent / "gandalf_ui_linter.py"
    if not linter_path.exists():
        return
    res = subprocess.run([sys.executable, str(linter_path)], capture_output=False)
    if res.returncode != 0:
        sys.exit(1)

def main():
    check_zero_ports()
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
        staged_files = []

    all_violations = []

    for fpath in staged_files:
        if not fpath.endswith(TARGET_EXTENSIONS):
            continue
        if any(ex in fpath for ex in EXCLUDED_PATHS):
            continue

        diff_proc = subprocess.run(
            ["git", "diff", "--cached", "--", fpath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        added_lines = [
            line[1:] for line in diff_proc.stdout.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        violations = scan_text("\n".join(added_lines), fpath)
        all_violations.extend(violations)

    if all_violations:
        print("\n" + "=" * 72, file=sys.stderr)
        print("🧙‍♂️ GANDALF PRE-COMMIT HOOK: \"YOU SHALL NOT PASS!\"", file=sys.stderr)
        print("=" * 72, file=sys.stderr)
        print("❌ Staged changes contain prompt leakage / word-salad in customer UI:\n", file=sys.stderr)
        for v in all_violations:
            print(f"  • {v['file']}:{v['line_number']}", file=sys.stderr)
            print(f"    Matched: \"{v['matched']}\"", file=sys.stderr)
            print(f"    Line:    {v['line_content']}\n", file=sys.stderr)
        print("🛑 Commit REJECTED. Remove prompt leakage before committing.", file=sys.stderr)
        print("=" * 72 + "\n", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
