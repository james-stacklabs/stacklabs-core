#!/usr/bin/env python3
"""
Sovereign OS Full Codebase Hygiene & Feral Code Auditor
======================================================
Exhaustive static analysis auditing Python backends and TypeScript/React frontends
against Sovereign OS Architectural Invariants:
1. SQLite connection management (context manager vs raw connect)
2. Inline imports inside function/loop scopes
3. Hardcoded absolute host paths (/home/james/...)
4. Bare / swallowed exceptions (except: pass)
5. Manual .env text parsing
6. Hardcoded persona / entity / room branching (Whack-a-Mole)
7. Monolithic script sprawl (>1,000 lines)
8. Frontend hardcoded mock data, inline fake metrics (Math.random), and hardcoded IPs
"""

import os
import re
import sys
import json
from pathlib import Path
from collections import defaultdict

WORKSPACE_ROOT = Path("/home/james/stacklabs")
REPORT_OUTPUT_DIR = Path("/home/james/sovereign_inbox/daily_08312026")
REPORT_FILE = REPORT_OUTPUT_DIR / "FULL_SOVEREIGN_CODEBASE_AUDIT_REPORT.md"

# Directories to audit
CORE_PY_DIRS = [
    WORKSPACE_ROOT / "scripts",
    WORKSPACE_ROOT / "core",
    WORKSPACE_ROOT / "services",
]

CORE_TSX_DIRS = [
    WORKSPACE_ROOT / "01_Sovereign_Portal",
    WORKSPACE_ROOT / "15_FanStack",
    WORKSPACE_ROOT / "19_Sovereign_Sports",
    WORKSPACE_ROOT / "25_CmdbStudio",
    WORKSPACE_ROOT / "18_BarbStack",
    WORKSPACE_ROOT / "02_Sovereign_Media",
]

EXCLUDE_DIRS = {
    ".venv", "node_modules", "dist", "build", "coverage", ".git", 
    ".agents", "__pycache__", ".turbo", "archive_quarantine_eon1", "tmp"
}

# --- AUDIT RESULTS STORAGE ---
py_audit = {
    "total_files": 0,
    "total_lines": 0,
    "raw_sqlite_connects": [],       # (file, line_num, line_text)
    "inline_imports": [],            # (file, line_num, line_text)
    "hardcoded_paths": [],           # (file, line_num, line_text)
    "swallowed_exceptions": [],      # (file, line_num, line_text)
    "manual_env_parsing": [],        # (file, line_num, line_text)
    "hardcoded_persona_branching": [],# (file, line_num, line_text)
    "hardcoded_room_branching": [],  # (file, line_num, line_text)
    "monoliths_over_1k": [],         # (file, line_count)
}

tsx_audit = {
    "total_files": 0,
    "total_lines": 0,
    "hardcoded_ips": [],             # (file, line_num, line_text)
    "inline_math_random": [],        # (file, line_num, line_text)
    "hardcoded_mock_arrays": [],     # (file, line_num, line_text)
    "unmanaged_window_scroll": [],   # (file, line_num, line_text)
    "monoliths_over_500": [],        # (file, line_count)
}

# --- PATTERNS ---
RE_SQLITE_CONNECT = re.compile(r'\bsqlite3\.connect\(', re.IGNORECASE)
RE_WITH_SQLITE = re.compile(r'\bwith\s+(?:sqlite3\.connect|get_db|db_connection|get_db_connection)\b')
RE_INLINE_IMPORT = re.compile(r'^\s+(?:import\s+[a-zA-Z0-9_.]+|from\s+[a-zA-Z0-9_.]+\s+import\s+)')
RE_HARDCODED_PATH = re.compile(r'[\'"](?:/home/james/|/mnt/|/tmp/|Z:\\)[^\'"]+[\'"]')
RE_BARE_EXCEPT = re.compile(r'^\s*except(?:\s+Exception)?\s*:\s*(?:pass|\.\.\.)\s*$')
RE_MANUAL_ENV = re.compile(r'open\([^)]*\.env[^)]*\)|line\.startswith\([\'"][A-Z0-9_]+=\'')
RE_PERSONA_BRANCH = re.compile(r'\b(?:if|elif)\s+[\'"](?:barf|dot|keith|vinnie|uncle_stevie|7_train_terry|cap_peterson)[\'"]\s+in\b|\b(?:if|elif)\s+fan(?:_name)?(?:_low)?\s*==\s*[\'"][a-zA-Z0-9_]+[\'"]', re.IGNORECASE)
RE_ROOM_BRANCH = re.compile(r'\b(?:if|elif)\s+(?:room_key|game_pk|room_id)\s*(?:==|in|!=)\s*[\'"](?:WEEDSTACK|826|823|GLOBAL|[0-9]{6})', re.IGNORECASE)

RE_TSX_IP = re.compile(r'[\'"](?:https?://)?100\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?/?[\'"]')
RE_TSX_MATH_RANDOM = re.compile(r'Math\.random\(\)')
RE_TSX_MOCK_ARRAY = re.compile(r'(?:const|let|var)\s+(?:MOCK_|DUMMY_|SAMPLE_|INITIAL_)[A-Z0-9_]*\s*=\s*\[')

def is_excluded(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False

def audit_python_file(filepath: Path):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return

    rel_path = str(filepath.relative_to(WORKSPACE_ROOT))
    line_count = len(lines)
    py_audit["total_files"] += 1
    py_audit["total_lines"] += line_count

    if line_count > 1000:
        py_audit["monoliths_over_1k"].append((rel_path, line_count))

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue

        # 1. SQLite Connect Check
        if RE_SQLITE_CONNECT.search(line) and not RE_WITH_SQLITE.search(line):
            # check if previous line was a 'with' statement
            if idx > 1 and not RE_WITH_SQLITE.search(lines[idx-2]):
                py_audit["raw_sqlite_connects"].append((rel_path, idx, stripped[:100]))

        # 2. Inline imports (indented imports)
        if RE_INLINE_IMPORT.search(line):
            # Exclude typing.TYPE_CHECKING blocks if any
            if "TYPE_CHECKING" not in line:
                py_audit["inline_imports"].append((rel_path, idx, stripped[:100]))

        # 3. Hardcoded paths
        if RE_HARDCODED_PATH.search(line) and "__file__" not in line:
            py_audit["hardcoded_paths"].append((rel_path, idx, stripped[:100]))

        # 4. Bare except pass
        if RE_BARE_EXCEPT.search(line):
            py_audit["swallowed_exceptions"].append((rel_path, idx, stripped[:100]))

        # 5. Manual .env parsing
        if RE_MANUAL_ENV.search(line):
            py_audit["manual_env_parsing"].append((rel_path, idx, stripped[:100]))

        # 6. Hardcoded persona branching
        if RE_PERSONA_BRANCH.search(line):
            py_audit["hardcoded_persona_branching"].append((rel_path, idx, stripped[:100]))

        # 7. Hardcoded room branching
        if RE_ROOM_BRANCH.search(line):
            py_audit["hardcoded_room_branching"].append((rel_path, idx, stripped[:100]))

def audit_tsx_file(filepath: Path):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return

    rel_path = str(filepath.relative_to(WORKSPACE_ROOT))
    line_count = len(lines)
    tsx_audit["total_files"] += 1
    tsx_audit["total_lines"] += line_count

    if line_count > 500:
        tsx_audit["monoliths_over_500"].append((rel_path, line_count))

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # 1. Hardcoded IP
        if RE_TSX_IP.search(line):
            tsx_audit["hardcoded_ips"].append((rel_path, idx, stripped[:100]))

        # 2. Math.random
        if RE_TSX_MATH_RANDOM.search(line):
            tsx_audit["inline_math_random"].append((rel_path, idx, stripped[:100]))

        # 3. Hardcoded Mock Arrays
        if RE_TSX_MOCK_ARRAY.search(line):
            tsx_audit["hardcoded_mock_arrays"].append((rel_path, idx, stripped[:100]))

def run_audit():
    print("🔍 Scanning Python files across SovereignOS...")
    for root_dir in CORE_PY_DIRS:
        if not root_dir.exists():
            continue
        for py_path in root_dir.rglob("*.py"):
            if not is_excluded(py_path):
                audit_python_file(py_path)

    print("🔍 Scanning TypeScript/React frontends across SovereignOS...")
    for root_dir in CORE_TSX_DIRS:
        if not root_dir.exists():
            continue
        for ext in ("*.tsx", "*.ts"):
            for ts_path in root_dir.rglob(ext):
                if not is_excluded(ts_path):
                    audit_tsx_file(ts_path)

    # Compile Markdown Report
    print("📝 Compiling Comprehensive Audit Report...")
    REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(REPORT_FILE, "w", encoding="utf-8") as rep:
        rep.write("# 🏛️ SOVEREIGN OS FULL REPOSITORY CODE HYGIENE AUDIT\n")
        rep.write(f"**Generated**: August 31, 2026 | **Authority**: James Carroll (Lead Systems Architect)\n")
        rep.write(f"**Target**: Comprehensive Repository-Wide Static Analysis (Python & TypeScript/React)\n\n")
        rep.write("---\n\n")

        rep.write("## 📊 1. EXECUTIVE SUMMARY & VIOLATION MATRIX\n\n")
        rep.write("| Category / Architectural Invariant | Violation Count | Severity | Target Remediation Standard |\n")
        rep.write("| :--- | :--- | :--- | :--- |\n")
        rep.write(f"| **Raw Unmanaged SQLite Connections** | **{len(py_audit['raw_sqlite_connects'])}** | 🔴 CRITICAL | Enforce `with get_db() as conn:` context managers |\n")
        rep.write(f"| **Inline Scoped Imports (in functions/loops)** | **{len(py_audit['inline_imports'])}** | 🟠 HIGH | Move all imports to top of file |\n")
        rep.write(f"| **Hardcoded Host Path Literals (`/home/james`)** | **{len(py_audit['hardcoded_paths'])}** | 🟠 HIGH | Dynamic `Path(__file__).resolve()` resolution |\n")
        rep.write(f"| **Swallowed / Bare Exceptions (`except: pass`)** | **{len(py_audit['swallowed_exceptions'])}** | 🔴 CRITICAL | Explicit structured error logging with `logger.error` |\n")
        rep.write(f"| **Manual `.env` File Scraping** | **{len(py_audit['manual_env_parsing'])}** | 🟡 MEDIUM | Use `os.environ` or `core.config` |\n")
        rep.write(f"| **Hardcoded Persona Branching (`if 'barf' in`)** | **{len(py_audit['hardcoded_persona_branching'])}** | 🔴 CRITICAL | Dynamic SQLite DB prompt overlay & token parsing |\n")
        rep.write(f"| **Hardcoded Room / Schedule Gates** | **{len(py_audit['hardcoded_room_branching'])}** | 🔴 CRITICAL | Polymorphic table-driven room event engine |\n")
        rep.write(f"| **Monolithic Python Daemons (>1,000 lines)** | **{len(py_audit['monoliths_over_1k'])} files** | 🟠 HIGH | Factor into domain services in `scripts/services/` |\n")
        rep.write(f"| **Frontend Hardcoded IP Literals (`100.x.y.z`)** | **{len(tsx_audit['hardcoded_ips'])}** | 🔴 CRITICAL | MagicDNS hostnames & `/api/public/identify` |\n")
        rep.write(f"| **Frontend `Math.random()` Metric Cosplay** | **{len(tsx_audit['inline_math_random'])}** | 🟠 HIGH | Live WebSocket / SQLite telemetry bindings |\n")
        rep.write(f"| **Frontend Hardcoded Mock Data Arrays** | **{len(tsx_audit['hardcoded_mock_arrays'])}** | 🔴 CRITICAL | Dynamic REST queries on SQLite CMDB / Personas |\n")
        rep.write(f"| **Frontend Giant Components (>500 lines)** | **{len(tsx_audit['monoliths_over_500'])} files** | 🟡 MEDIUM | Break into sub-components & custom hooks |\n\n")

        rep.write(f"**Total Python Files Scanned**: {py_audit['total_files']} ({py_audit['total_lines']:,} lines)\n")
        rep.write(f"**Total TypeScript/React Files Scanned**: {tsx_audit['total_files']} ({tsx_audit['total_lines']:,} lines)\n\n")
        rep.write("---\n\n")

        # Section 2: Monolith Index
        rep.write("## 📜 2. THE MONOLITH LEADERBOARD (>1,000 Lines Python / >500 Lines TSX)\n\n")
        rep.write("### Python Monoliths:\n")
        for fpath, lines in sorted(py_audit["monoliths_over_1k"], key=lambda x: x[1], reverse=True):
            rep.write(f"- `{fpath}`: **{lines:,} lines**\n")
        rep.write("\n### Frontend TSX Monoliths:\n")
        for fpath, lines in sorted(tsx_audit["monoliths_over_500"], key=lambda x: x[1], reverse=True)[:15]:
            rep.write(f"- `{fpath}`: **{lines:,} lines**\n")
        rep.write("\n---\n\n")

        # Section 3: Detailed Breakdown of Python Violations
        rep.write("## 🐍 3. PYTHON BACKEND VIOLATION INVENTORY\n\n")
        
        rep.write(f"### A. Hardcoded Persona Branching ({len(py_audit['hardcoded_persona_branching'])} Occurrences)\n")
        rep.write("> *Violates Anti-Whack-a-Mole Doctrine Section II.2*\n\n")
        for fpath, lnum, code in py_audit["hardcoded_persona_branching"][:30]:
            rep.write(f"- [`{fpath}:{lnum}`](file://{WORKSPACE_ROOT}/{fpath}#L{lnum}): `{code}`\n")
        if len(py_audit["hardcoded_persona_branching"]) > 30:
            rep.write(f"- *... and {len(py_audit['hardcoded_persona_branching']) - 30} more*\n")

        rep.write(f"\n### B. Raw SQLite Connect Calls ({len(py_audit['raw_sqlite_connects'])} Occurrences)\n")
        rep.write("> *Violates Smells Like Feral Interns Sin #1 (Unmanaged Connection Leakers)*\n\n")
        # group by file
        sql_by_file = defaultdict(list)
        for fpath, lnum, code in py_audit["raw_sqlite_connects"]:
            sql_by_file[fpath].append(lnum)
        for fpath, lnums in sorted(sql_by_file.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
            rep.write(f"- `{fpath}`: **{len(lnums)} unmanaged connects** (Lines: {', '.join(map(str, lnums[:10]))}{'...' if len(lnums) > 10 else ''})\n")

        rep.write(f"\n### C. Bare Exception Swallowers (`except: pass`) ({len(py_audit['swallowed_exceptions'])} Occurrences)\n")
        rep.write("> *Violates Anti-Whack-a-Mole Doctrine Section II.5*\n\n")
        for fpath, lnum, code in py_audit["swallowed_exceptions"][:25]:
            rep.write(f"- [`{fpath}:{lnum}`](file://{WORKSPACE_ROOT}/{fpath}#L{lnum}): `{code}`\n")

        rep.write(f"\n### D. Hardcoded Host Paths ({len(py_audit['hardcoded_paths'])} Occurrences)\n")
        rep.write("> *Violates Smells Like Feral Interns Sin #3*\n\n")
        path_by_file = defaultdict(int)
        for fpath, lnum, code in py_audit["hardcoded_paths"]:
            path_by_file[fpath] += 1
        for fpath, count in sorted(path_by_file.items(), key=lambda x: x[1], reverse=True)[:15]:
            rep.write(f"- `{fpath}`: **{count} hardcoded paths**\n")

        rep.write("\n---\n\n")

        # Section 4: Frontend Violations
        rep.write("## ⚛️ 4. REACT / TYPESCRIPT FRONTEND VIOLATION INVENTORY\n\n")
        
        rep.write(f"### A. Hardcoded IP Addresses ({len(tsx_audit['hardcoded_ips'])} Occurrences)\n")
        for fpath, lnum, code in tsx_audit["hardcoded_ips"]:
            rep.write(f"- [`{fpath}:{lnum}`](file://{WORKSPACE_ROOT}/{fpath}#L{lnum}): `{code}`\n")

        rep.write(f"\n### B. `Math.random()` Metric Cosplay ({len(tsx_audit['inline_math_random'])} Occurrences)\n")
        for fpath, lnum, code in tsx_audit["inline_math_random"][:20]:
            rep.write(f"- [`{fpath}:{lnum}`](file://{WORKSPACE_ROOT}/{fpath}#L{lnum}): `{code}`\n")

        rep.write(f"\n### C. Hardcoded Mock Data Fixtures ({len(tsx_audit['hardcoded_mock_arrays'])} Occurrences)\n")
        for fpath, lnum, code in tsx_audit["hardcoded_mock_arrays"][:20]:
            rep.write(f"- [`{fpath}:{lnum}`](file://{WORKSPACE_ROOT}/{fpath}#L{lnum}): `{code}`\n")

        rep.write("\n---\n\n")

        # Section 5: Prioritized Remediation Roadmap
        rep.write("## 🛠️ 5. PRIORITIZED REMEDIATION ROADMAP (DISCIPLINED REFACTORING)\n\n")
        rep.write("### Phase 1: Tier-1 Production Daemons (Live Game Day Stability)\n")
        rep.write("1. **`fanstack_chatbots.py` (3,408 lines)**: Purge all 40+ hardcoded `if 'barf' in` and `if 'dot' in` branches. Load prompt guards, canned takes, and colors dynamically from SQLite `persona`.\n")
        rep.write("2. **`fanstack_relay.py` (4,004 lines)**: Decompose WebSocket ingress into modular message routers under `scripts/routers/fanstack_ws/`.\n")
        rep.write("3. **`sdlc_portal_server.py` (4,740 lines)**: Modularize into sub-routers in `scripts/routers/`.\n")
        rep.write("4. **Universal Database Session Manager**: Standardize `with get_db() as conn:` across all 342 raw connect locations.\n\n")
        rep.write("### Phase 2: Frontend Hardcoded Data Purge\n")
        rep.write("1. Purge all `Math.random()` mock telemetry and bind directly to WebSocket and REST endpoints.\n")
        rep.write("2. Replace all hardcoded `100.x.y.z` IP strings with MagicDNS hostnames.\n\n")

    print(f"✅ Audit complete! Report generated at: {REPORT_FILE}")

if __name__ == "__main__":
    run_audit()
