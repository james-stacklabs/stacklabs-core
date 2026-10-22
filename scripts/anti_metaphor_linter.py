#!/usr/bin/env python3
"""
StackLabs Anti-Metaphor & Invariant 38 Lexical Circuit Breaker
Author: James Carroll (Pilot), Lead Systems Architect

Strictly enforces Invariant 38 (Zero Metaphor Leakage), Invariant 38.1 (Ripperdoc Invariant),
and Gandalf UI Craft.
Scans codebases and sprint documentation for:
1. Brainstorm analogies, chat metaphors, and pop-culture slang ("Best Buy", "Pepe Silvia", "Ant Farm", etc.)
2. Cyberpunk RPG & Sci-Fi Cyberware Slop ("Reflex Coprocessor", "Neural Mesh", "Ripperdoc", etc.)
3. Leaked developer coordinates, internal ports, hostnames, and IP addresses.
4. Bracketed void-panic badges and hacker slashes.

Exits with non-zero exit code on any violation, blocking builds and deployments.
"""

import sys
import os
import re
from pathlib import Path

# Banned exact or substring phrases (case-insensitive)
BANNED_METAPHORS = [
    # Conversational Analogies & Pop Culture Slang
    "best buy",
    "best buy showroom",
    "pepe silvia",
    "ant farm",
    "shaking the ant farm",
    "zeus on mount olympus",
    "trash can",
    "cosplay",
    "toy app",
    "comic book",
    "script kiddie",
    "charlie kelly",
    "mailroom conspiracy",
    "yarn strings",
    "whiteboard yarn",
    "projector cart",
    "timeline pruning",
    "zero mocks",
    "1x metal",

    # Internal Coordinate & Hostname Leakage
    "/home/james",
    "home/james",
    "/dev/shm",
    "clio bare metal",
    "port 3025",
    "port 3033",
    "port 8088",
    "port 8095",
    "port 8008",
    "clio metal",
    "clio forge",
    "100.96.77.20",
    "100.108.185.53",
    "rule zero",
    "invariant 26",
    "invariant 38",
    "invariant 39",
    "invariant 0",
    "system prompt",
    "prompt leakage",

    # Cyberpunk RPG & Sci-Fi Cyberware Slop (Invariant 38.1 Expansion)
    "reflex coprocessor",
    "reflex co-processor",
    "l1 reflex",
    "l1 coprocessor",
    "spinal cord",
    "nervous system",
    "reflex arc",
    "symbiotic coprocessor",
    "eurobucks",
    "ripperdoc",
    "humanity loss",
    "cyberware",
    "wetware",
    "arasaka",
    "night city",
    "omega gate",
    "omega-gate",
    "bare metal forge",
    "metal forge",

    # Retail Appliance & Consumer Hardware Slop (Invariant 1.8)
    "mini pc",
    "mini-pc",
    "micro pc",
    "micro-pc",
    "35-watt",
    "35 watt",
    "35w ",
    "35w footprint",
    "35w appliance",
    "appliance box",
    "hardware box",
    "hardware appliance",
    "incandescent light bulb",
    "light bulb",
]

BANNED_STRUCTURAL_PATTERNS = [
    (re.compile(r'\[(DUAL-RUNNER|L1 REFLEX METAL|WAN REST|POSIX SYMLINK MESH|ACTIVE FAILOVER|STANDBY|ISOLATED DRAIN)\]'), "Banned bracketed void-panic badge"),
    (re.compile(r'>\s*[^<]*\b[a-zA-Z0-9]+\s+//\s+[a-zA-Z0-9]+[^<]*<'), "Hacker slash (//) in user-facing UI copy"),
    (re.compile(r'>\s*[^<]*\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b[^<]*<'), "Internal Tailscale IP leaked in user-facing UI copy"),
    (re.compile(r'>\s*[^<]*\bPort\s+[0-9]{4,5}\b[^<]*<', re.IGNORECASE), "Port number leaked in user-facing UI copy"),
]

OPSEC_BLUEPRINT_LEAKS = [
    "/dev/shm",
    "dev/shm",
    "st_ino",
    "shm_inode",
    "db_inode",
    "sqlite_wal",
    "sqlite wal",
    "sqlite",
    "symlink",
    "virtual file system",
    "posix",
    "tmpfs",
    "sysfs",
    "inode",
    "wal page",
    "wal_page",
    "shootout_vfs",
]

CODE_EXTENSIONS = {'.tsx', '.ts', '.jsx', '.js', '.html'}
DOC_EXTENSIONS = {'.md', '.txt'}
IGNORE_DIRS = {
    'node_modules', 'dist', '.git', '.wrangler', '.venv', '__pycache__',
    'archive', 'legacy', '.staging', 'coverage'
}


def scan_file(file_path: Path, is_doc: bool = False) -> list[tuple[int, str, str]]:
    violations = []
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return violations

    lines = content.splitlines()
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not is_doc and (stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*') or stripped.startswith('#')):
            continue

        lower = line.lower()
        for banned in BANNED_METAPHORS:
            if banned in lower:
                if "anti_metaphor_linter" in str(file_path) or "verify_cyberpunk" in str(file_path) or "purge_coprocessor" in str(file_path):
                    continue
                violations.append((line_no, stripped, f"Banned metaphor/slop: '{banned}'"))
                break

        if not is_doc:
            for leak in OPSEC_BLUEPRINT_LEAKS:
                if leak in lower:
                    if "anti_metaphor_linter" in str(file_path):
                        continue
                    violations.append((line_no, stripped, f"OPSEC_BLUEPRINT_LEAK: Trade-secret implementation primitive '{leak}' exposed in UI code"))
                    break

            for pattern, desc in BANNED_STRUCTURAL_PATTERNS:
                match = pattern.search(line)
                if match:
                    violations.append((line_no, stripped, f"{desc}: '{match.group(0)}'"))
                    break

    return violations


def run_linter(targets: list[Path], scan_docs: bool = False) -> int:
    all_violations = []
    valid_exts = CODE_EXTENSIONS | (DOC_EXTENSIONS if scan_docs else set())

    for target in targets:
        if not target.exists():
            continue
        if target.is_file():
            is_doc = target.suffix in DOC_EXTENSIONS
            if target.suffix in valid_exts:
                v = scan_file(target, is_doc=is_doc)
                for line_no, code_line, reason in v:
                    all_violations.append((str(target), line_no, code_line, reason))
            continue

        for root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for f in files:
                p = Path(root) / f
                is_doc = p.suffix in DOC_EXTENSIONS
                if p.suffix in valid_exts:
                    v = scan_file(p, is_doc=is_doc)
                    for line_no, code_line, reason in v:
                        rel = p
                        try:
                            rel = p.relative_to(target.parent if target.parent else target)
                        except ValueError:
                            pass
                        all_violations.append((str(rel), line_no, code_line, reason))

    if all_violations:
        print("\033[91m\033[1m" + "=" * 80)
        print("🧙‍♂️ [GANDALF ANTI-METAPHOR CIRCUIT BREAKER] BUILD HALTED: SLOP DETECTED")
        print("=" * 80 + "\033[0m")
        for file_path, line_no, code_line, reason in all_violations:
            print(f"\033[93m❌ VIOLATION:\033[0m {file_path}:{line_no}")
            print(f"   \033[91m-> {code_line}\033[0m")
            print(f"   \033[90mReason: {reason}\033[0m\n")
        print("\033[91mRule: Chat analogies, cyberpunk cyberware terms ('Reflex Coprocessor', 'Ripperdoc'), and coordinate leaks are banned.\033[0m\n")
        return 1

    print("\033[92m✔ [GANDALF ANTI-METAPHOR GATE] PASSED: Zero conversational metaphors, cyberware slop, or leaked coordinates detected.\033[0m")
    return 0


if __name__ == "__main__":
    scan_docs = False
    args = sys.argv[1:]
    if "--artifacts" in args:
        scan_docs = True
        args.remove("--artifacts")

    if args:
        scan_paths = [Path(arg).resolve() for arg in args]
    else:
        root = Path(__file__).resolve().parent.parent
        if scan_docs:
            scan_paths = [
                root / "artifacts" / "sprints",
                root / "dna" / "docs",
            ]
        else:
            scan_paths = [
                root / "apps" / "cmdb_studio" / "src",
                root / "apps" / "faas" / "src",
                root / "frontend"
            ]

    sys.exit(run_linter(scan_paths, scan_docs=scan_docs))
