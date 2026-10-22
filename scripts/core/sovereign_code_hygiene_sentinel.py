#!/usr/bin/env python3
"""
sovereign_code_hygiene_sentinel.py
=============================================================================
SOVEREIGN OS: CODE HYGIENE & ANTI-FLUFF SENTINEL (STATIC AUDIT ENGINE)
=============================================================================
Enforces strict enterprise invariants, zero-tolerance hardcoding rules,
FastAPI-first mandates, and anti-fluff style fences across the codebase.
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

class Violation(NamedTuple):
    severity: str        # CRITICAL, MAJOR, MINOR
    v_type: str          # Violation category
    file_path: str       # Relative file path
    line_num: int        # 1-indexed line number
    snippet: str         # Code snippet showing violation
    remediation: str     # Actionable fix instruction

class SovereignHygieneSentinel:
    """Static analysis scanner enforcing Sovereign OS invariants."""

    # 1. Zero Hardcoding & Fake Data Arbitrage (CRITICAL)
    MOCK_PATTERNS = [
        (re.compile(r"""(?:scores|boxscore|statcast_speed|pitch_speed)\s*=\s*\{["'][A-Z]{2,3}["']\s*:"""), 
         "CRITICAL", "Hardcoded Mock Data", "Fetch data dynamically via live Statcast feed, SQLite DB, or API client."),
        (re.compile(r"""(?:return|status)\s*=\s*\{["']simulated["']\s*:\s*True\}"""), 
         "CRITICAL", "Simulated Telemetry Arbitrage", "Replace simulation wrapper with active DB/REST payload."),
        (re.compile(r"""const\s+(?:liveScores|mockGames|fakeOdds)\s*=\s*\["""),
         "CRITICAL", "Hardcoded Live State Array", "Bind UI components to live WebSocket state or REST endpoints."),
    ]

    # 2. FastAPI-First Law / No Raw SQLite Subshells (MAJOR)
    SQLITE_BYPASS_PATTERNS = [
        (re.compile(r"""sqlite3\.(?:connect|execute)\("""), 
         "MAJOR", "Raw SQLite Driver Call", "Route state mutations through FastAPI (port 8095) or scripts/core/api_client.py."),
        (re.compile(r"""python3?\s+-c\s+["'].*import\s+sqlite3.*["']"""), 
         "MAJOR", "Raw SQLite CLI Subshell", "Execute operations using Sovereign REST endpoints or API client SDK."),
    ]

    # 3. Sci-Fi Fluff & Cyberpunk Buzzwords (MINOR / MAJOR)
    FLUFF_PATTERNS = [
        (re.compile(r"""(?i)["'](cognitive[-_\s]?lock|quantum[-_\s]?neural|neural[-_\s]?sync|1000%\s*secure|cyber[-_\s]?matrix|tactile[-_\s]?relay)["']"""), 
         "MINOR", "Sci-Fi Fluff Metric", "Replace fictional buzzwords with real telemetry, node states, or port numbers."),
        (re.compile(r"""(?i)["'](5\.1V\s*power\s*rail|voltage\s*sag\s*simulation)["']"""),
         "MAJOR", "Fabricated Hardware Spec", "Remove fabricated hardware metrics. Reference real sensor readings."),
    ]

    # 4. UI Completeness & Button Interaction Stubs (MAJOR / MINOR)
    UI_STUB_PATTERNS = [
        (re.compile(r"""(?:onClick|onChange|onSubmit)\s*=\s*\{\s*\(\s*\)\s*=>\s*\{\s*\}\s*\}"""), 
         "MAJOR", "Stubbed Empty UI Handler", "Wire handler to an active state dispatch or REST API mutation."),
        (re.compile(r"""(?:onClick|onChange)\s*=\s*\{\s*\(\s*\)\s*=>\s*console\.log\("""), 
         "MINOR", "Console Log Stub Handler", "Replace debug console.log with actual business logic or action dispatch."),
    ]

    # 5. Dangerous Swallowed Exceptions & Scoped Hacks (MAJOR)
    CODE_HYGIENE_PATTERNS = [
        (re.compile(r"""except\s*:\s*pass"""),
         "MAJOR", "Swallowed Exception", "Catch specific exception classes and log actionable error context."),
        (re.compile(r"""100\.\d{1,3}\.\d{1,3}\.\d{1,3}"""),
         "MINOR", "Hardcoded Tailscale IP", "Use MagicDNS hostnames (e.g. clio.taila01894.ts.net) rather than raw IPs."),
    ]

    # Whitelisted core database backend files permitted to invoke sqlite3 directly
    CORE_DB_WHITELIST = {
        "scripts/core/db.py",
        "scripts/sdlc_portal_server.py",
        "scripts/tmi_daemon.py",
        "scripts/fanstack_relay.py",
        "scripts/fanstack_chatbots.py",
        "scripts/core/offline_corpus_engine.py",
        "scripts/hooks/sovereign_guardrail_hook.py",
        "scripts/routers/",
    }

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = Path(repo_root or "/home/james/stacklabs").resolve()

    def is_whitelisted_db_file(self, rel_path: str) -> bool:
        norm_path = str(rel_path).replace("\\", "/")
        for wl in self.CORE_DB_WHITELIST:
            if norm_path.endswith(wl) or wl in norm_path:
                return True
        return False

    def scan_file(self, file_path: Path) -> List[Violation]:
        violations: List[Violation] = []
        try:
            rel_path = file_path.resolve().relative_to(self.repo_root)
        except ValueError:
            rel_path = file_path

        rel_str = str(rel_path).replace("\\", "/")

        # Skip vendor, git, cache, node_modules, and virtualenvs
        if any(ignored in rel_str for ignored in [
            "node_modules", ".venv", ".git", "dist", "build", 
            "__pycache__", ".tempmediaStorage", "vendor"
        ]):
            return violations

        is_whitelisted_db = self.is_whitelisted_db_file(rel_str)
        is_frontend = file_path.suffix in [".tsx", ".jsx", ".vue", ".html"]
        is_python = file_path.suffix == ".py"
        is_shell = file_path.suffix == ".sh"

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return violations

        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith(("#", "//", "/*", "*")):
                continue

            # Check 1: Mock data
            for pattern, sev, v_type, rem in self.MOCK_PATTERNS:
                if pattern.search(line_str):
                    violations.append(Violation(sev, v_type, rel_str, idx, line_str[:70], rem))

            # Check 2: Raw SQLite bypass
            if not is_whitelisted_db:
                for pattern, sev, v_type, rem in self.SQLITE_BYPASS_PATTERNS:
                    if pattern.search(line_str):
                        violations.append(Violation(sev, v_type, rel_str, idx, line_str[:70], rem))

            # Check 3: Fluff & Buzzwords
            for pattern, sev, v_type, rem in self.FLUFF_PATTERNS:
                if pattern.search(line_str):
                    violations.append(Violation(sev, v_type, rel_str, idx, line_str[:70], rem))

            # Check 4: Frontend UI stubs
            if is_frontend:
                for pattern, sev, v_type, rem in self.UI_STUB_PATTERNS:
                    if pattern.search(line_str):
                        violations.append(Violation(sev, v_type, rel_str, idx, line_str[:70], rem))

            # Check 5: General hygiene
            if is_python or is_shell:
                for pattern, sev, v_type, rem in self.CODE_HYGIENE_PATTERNS:
                    if pattern.search(line_str):
                        violations.append(Violation(sev, v_type, rel_str, idx, line_str[:70], rem))

        return violations

    def scan_path(self, target_path: str) -> List[Violation]:
        target = Path(target_path).resolve()
        violations: List[Violation] = []

        if target.is_file():
            violations.extend(self.scan_file(target))
        elif target.is_dir():
            for root, _, files in os.walk(target):
                for f in files:
                    ext = Path(f).suffix.lower()
                    if ext in [".py", ".sh", ".tsx", ".ts", ".jsx", ".js"]:
                        violations.extend(self.scan_file(Path(root) / f))
        return violations

    def generate_report(self, target_path: str, violations: List[Violation], as_json: bool = False) -> str:
        criticals = any(v.severity == "CRITICAL" for v in violations)
        majors = any(v.severity == "MAJOR" for v in violations)

        if criticals or majors:
            verdict = "❌ REJECTED"
        elif violations:
            verdict = "⚠️ WARNINGS"
        else:
            verdict = "✅ PASS"

        if as_json:
            return json.dumps({
                "target": target_path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "verdict": verdict,
                "total_violations": len(violations),
                "violations": [v._asdict() for v in violations]
            }, indent=2)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            "# 🚨 SOVEREIGN CODE HYGIENE AUDIT REPORT",
            f"**Target Inspected**: `{target_path}`",
            f"**Audit Timestamp**: {ts}",
            f"**Verdict**: **{verdict}** (Total Violations: {len(violations)})\n",
            "### 🔍 Summary of Violations Found",
            "| Severity | Violation Type | File & Line Number | Exact Snippet | Remediation Required |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        if not violations:
            lines.append("| **NONE** | No Violations | N/A | Clean codebase verified. Zero fluff / zero hardcoding. | None |")
        else:
            for v in violations:
                clean_snippet = v.snippet.replace("|", "\\|")
                lines.append(f"| **{v.severity}** | {v.v_type} | `{v.file_path}:L{v.line_num}` | `{clean_snippet}` | {v.remediation} |")

        lines.append("\n### 🛠️ Required Fixes")
        if not violations:
            lines.append("1. None. All audited files strictly adhere to Sovereign OS architectural invariants.")
        else:
            for idx, v in enumerate(violations, start=1):
                lines.append(f"{idx}. **[{v.file_path}:L{v.line_num}]** {v.remediation}")

        return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Sovereign Code Hygiene & Anti-Fluff Sentinel")
    parser.add_argument("target", nargs="?", default=".", help="File or directory path to audit")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--fail-fast", action="store_true", help="Exit with code 1 immediately if violations found")
    args = parser.parse_args()

    sentinel = SovereignHygieneSentinel()
    violations = sentinel.scan_path(args.target)
    report = sentinel.generate_report(args.target, violations, as_json=args.json)
    print(report)

    if args.fail_fast and any(v.severity in ["CRITICAL", "MAJOR"] for v in violations):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
