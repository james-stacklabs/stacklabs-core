#!/usr/bin/env python3
"""
StackLabs Platform: Counterparty Hygiene & Zero-Tolerance Linter
Path: /home/james/stacklabs/scripts/verify_counterparty_hygiene.py

Governing Policy:
- Absolute ban on cynical slang ("whale", "whales", "the mark", "easy mark", "supergoop guy").
- Enforces professional counterparty classifications (Pawel Rudnicki, J. Stephen Emery, Jeremy Malone).
- Enforces total decommissioning of legacy sovereign-sdlc systemd alias.
- Exit code 0 on clean pass; Exit code 1 on any violation.
"""

import sys
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")

# Patterns strictly banned in active text
BANNED_REGEXES = [
    (re.compile(r"\bwhales?\b", re.IGNORECASE), "Cynical slang: 'whale' / 'whales'"),
    (re.compile(r"\b(the\s+mark|easy\s+mark)\b", re.IGNORECASE), "Cynical slang: 'the mark' / 'easy mark'"),
    (re.compile(r"\bsupergoop\s+guy\b", re.IGNORECASE), "Disrespectful moniker: 'supergoop guy'"),
]

# Context exceptions: lines defining the ban itself
EXEMPTION_PATTERNS = [
    "BANNED_REGEXES",
    "BANNED_PATTERNS",
    "permanently banned",
    "categorically banned",
    "absolute ban",
    "ban on cynical",
    "PURGE CYNICAL",
    "purge cynical",
    "verify_counterparty_hygiene",
    "banned slang",
    "prohibited slang",
    "cynical slang",
    "cynical counterparty jargon",
    "cynical monikers",
    "cynical lab slang",
]

TARGET_SCAN_PATHS = [
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / ".agents" / "rules",
    REPO_ROOT / ".agents" / "skills",
    REPO_ROOT / "ground_truth",
    REPO_ROOT / "pilot_drops" / "PILOT_PASSPORT_CURRENT.md",
    REPO_ROOT / "pilot_drops" / "pilot_scratch_pad.md",
    REPO_ROOT / "scripts" / "sync_pilot_passport.py",
    REPO_ROOT / "scripts" / "sdlc_portal_server.py",
]

def is_line_exempt(line: str) -> bool:
    for pat in EXEMPTION_PATTERNS:
        if pat.lower() in line.lower():
            return True
    return False

def check_file_hygiene(file_path: Path) -> list:
    violations = []
    if not file_path.exists():
        return violations

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        violations.append((file_path, 0, f"Failed to read file: {e}"))
        return violations

    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        if is_line_exempt(line):
            continue
        for regex, desc in BANNED_REGEXES:
            match = regex.search(line)
            if match:
                violations.append((file_path, idx, f"{desc} -> '{match.group(0)}' in: {line.strip()[:100]}"))
    return violations

def check_systemd_decommission() -> list:
    violations = []
    sovereign_sdlc = Path("/etc/systemd/system/sovereign-sdlc.service")
    if sovereign_sdlc.exists() or sovereign_sdlc.is_symlink():
        violations.append(("systemd", 0, f"Legacy alias exists: {sovereign_sdlc} must be purged."))

    # Verify canonical service is active
    try:
        res = subprocess.run(["systemctl", "is-active", "stacklabs-sdlc.service"], capture_output=True, text=True)
        if res.stdout.strip() != "active":
            violations.append(("systemd", 0, f"Canonical service stacklabs-sdlc.service is not active (state: {res.stdout.strip()})"))
    except Exception as e:
        violations.append(("systemd", 0, f"Failed to inspect stacklabs-sdlc.service: {e}"))

    return violations

def main():
    print("=" * 70)
    print("🛡️  STACKLABS COUNTERPARTY HYGIENE & GOVERNANCE LINTER")
    print("=" * 70)

    all_violations = []

    # 1. Scan target files and directories
    for target in TARGET_SCAN_PATHS:
        if target.is_file():
            all_violations.extend(check_file_hygiene(target))
        elif target.is_dir():
            for p in target.rglob("*"):
                if p.is_file() and p.suffix in [".md", ".py", ".sh", ".json", ".txt"]:
                    # Skip binary or cache directories
                    if any(part in p.parts for part in [".venv", "node_modules", "__pycache__", ".git"]):
                        continue
                    all_violations.extend(check_file_hygiene(p))

    # 2. Check systemd state
    all_violations.extend(check_systemd_decommission())

    # Report results
    if all_violations:
        print(f"\n❌ FAILED: Found {len(all_violations)} counterparty hygiene / governance violations:\n")
        for loc, line_no, detail in all_violations:
            loc_str = str(loc) if isinstance(loc, (str, Path)) else "system"
            if line_no > 0:
                print(f"  • [{loc_str}:{line_no}] {detail}")
            else:
                print(f"  • [{loc_str}] {detail}")
        print("\nFix all violations before proceeding.")
        sys.exit(1)
    else:
        print("\n✅ PASSED: 0 counterparty hygiene violations detected.")
        print("  • All governance rules, skills, and scripts are free of cynical slang.")
        print("  • Pawel Rudnicki, J. Stephen Emery, and Jeremy Malone classifications respected.")
        print("  • Legacy sovereign-sdlc.service is decommissioned.")
        print("  • Canonical stacklabs-sdlc.service is active on metal.")
        sys.exit(0)

if __name__ == "__main__":
    main()
