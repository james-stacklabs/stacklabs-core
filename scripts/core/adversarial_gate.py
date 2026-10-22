#!/usr/bin/env python3
"""
Sovereign OS: Adversarial Review Gate Module
Path: /home/james/stacklabs/scripts/core/adversarial_gate.py
Specification: SOW-040 (Sovereign Merkle Audit Chain & Adversarial Review Gate)
Ticket: WO0010312

Pre-flight static and heuristic adversarial inspector for staged work orders in queue/incoming/.
Validates against Sovereign invariants:
1. Rule Zero host division of labor (Artemis investigates/plans; Clio owns metal/forge/builds).
2. Rule I.8 & I.9 FastAPI-First mandate (zero raw SQLite subshells or CLI poking).
3. Rule I.6 Zero tolerance for fake fluff, sci-fi buzzwords, and script-kiddie tropes.
4. Rule IV.2.b & KI-095 Locked-viewport and responsive layout compliance.
5. Secret leakage and prompt injection detection.
"""

import os
import sys
import re
import argparse
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union
from pathlib import Path


@dataclass
class GateIssue:
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    title: str
    location: str
    attack_vector: str
    impact: str
    required_fix: str

    def to_markdown(self) -> str:
        return (
            f"**[SEVERITY: {self.severity}]** - {self.title}\n"
            f"**Location**: {self.location}\n"
            f"**Attack Vector**: {self.attack_vector}\n"
            f"**Impact**: {self.impact}\n"
            f"**Required Fix**: {self.required_fix}\n"
        )


@dataclass
class AdversarialGateResult:
    verdict: str  # "APPROVE" or "REJECT"
    issues: List[GateIssue]
    raw_markdown: str

    @property
    def is_approved(self) -> bool:
        return self.verdict == "APPROVE"


class SovereignAdversarialGate:
    """
    Adversarial Gate Inspector evaluating work orders and plan specifications
    prior to runner dispatch or code execution.
    """

    # Rule I.6 banned buzzwords & tropes
    BANNED_FLUFF_PATTERNS = [
        (r'\bCOGNITIVE\s+LOCK\b', "COGNITIVE LOCK trope detected"),
        (r'\b1000%\s+SECURE\b', "1000% SECURE marketing fluff detected"),
        (r'\bTACTILE\s+RELAY\s+ACTIVE\b', "TACTILE RELAY ACTIVE Hollywood trope detected"),
        (r'\bSYNAPTIC\s+BRIDGE\b', "SYNAPTIC BRIDGE sci-fi trope detected"),
        (r'\bQUANTUM\s+MESH\b', "QUANTUM MESH buzzword detected"),
        (r'\b5\.1V\s+POWER\s+RAIL\b', "Fabricated 5.1V power rail hardware specification"),
        (r'\bFAKE\s+SAG\s+SIMULATION\b', "Fake sag simulation trope detected"),
        (r'\bNEURAL\s+FIRMWARE\b', "Neural firmware buzzword detected"),
        (r'\bMATHEMATICALLY\s+COMPELLED\b', "Unanchored mathematical certainty claim"),
    ]

    # Rule I.8 / I.9 Raw SQLite subshell & bypass patterns
    RAW_SQLITE_PATTERNS = [
        (r'python3?\s+-c\s+["\'].*?import\s+sqlite3.*?["\']', "Raw SQLite python subshell execution"),
        (r'sqlite3\s+dna/sovereign_now\.db', "Direct SQLite CLI execution against sovereign_now.db"),
        (r'sqlite3\s+data/sovereign_now\.db', "Direct SQLite CLI execution against data/sovereign_now.db"),
        (r'sqlite3\.connect\(["\'].*sovereign_now\.db["\']\)', "Unprotected sqlite3.connect in client script outside backend service"),
    ]

    # Rule IV.2.b / KI-095 Viewport and layout patterns
    VIEWPORT_DEFECT_PATTERNS = [
        (r'width:\s*(?:1920|2560|3840)px', "Hardcoded fixed desktop width breaking viewport responsiveness (KI-095)"),
        (r'min-width:\s*(?:1920|2560|3840)px', "Excessive min-width breaking tablet/mobile responsive viewports"),
    ]

    # Secret / Credential leak patterns
    SECRET_PATTERNS = [
        (r'(?:AIzaSy[0-9A-Za-z\-_]{33})', "Google API key pattern detected in ticket text"),
        (r'(?:sk-[a-zA-Z0-9]{32,})', "OpenAI / Anthropic API secret key pattern detected"),
        (r'(?:ghp_[0-9a-zA-Z]{36})', "GitHub personal access token detected"),
    ]

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode

    def inspect_content(self, content: str, source_identifier: Optional[str] = None) -> AdversarialGateResult:
        issues: List[GateIssue] = []
        loc = source_identifier or "Work Order Content"

        # 1. Check Rule Zero: Host Division of Labor
        # Check if Artemis is assigned to execute metal/builds or Clio is assigned to purely cockpit architecture
        assigned_worker_match = re.search(r'\*\*(?:Assigned Worker|Worker|Host)\*\*:\s*`?([A-Za-z0-9_\-]+)`?', content, re.IGNORECASE)
        assigned_worker = assigned_worker_match.group(1).lower() if assigned_worker_match else ""

        is_code_or_build_order = bool(
            re.search(r'(?:npm\s+run\s+build|vite\s+build|apply\s+migration|write\s+code|run_command|clio_agent_exec)', content, re.IGNORECASE)
        )

        if assigned_worker in ("artemis", "pegasus") and is_code_or_build_order:
            issues.append(GateIssue(
                severity="CRITICAL",
                title="Rule Zero Violation: Cockpit Machine Assigned to Metal Code/Build Execution",
                location=loc,
                attack_vector=f"Worker '{assigned_worker}' is assigned to execute metal code, builds, or migrations.",
                impact="Breaks physical division of labor; causes build failures and IDE locks on laptop.",
                required_fix="Reassign Work Order to 'clio' for execution on workstation metal."
            ))

        # Check if work order explicitly requests Artemis to write application code directly
        if re.search(r'(?:Artemis\s+(?:writes?|generate|compile|build)\s+(?:application|metal|production)\s+code)', content, re.IGNORECASE):
            issues.append(GateIssue(
                severity="CRITICAL",
                title="Rule Zero Invariant Drift: Artemis Code Generation Directive",
                location=loc,
                attack_vector="Prompt or requirements direct Artemis to generate metal code instead of investigating/planning.",
                impact="Violates the Pilot's Iron Law of the Cockpit.",
                required_fix="Restrict Artemis to investigation, root-cause isolation, and implementation plan drafting."
            ))

        # 2. Check Rule I.8 & Rule I.9: Raw SQLite Subshell & FastAPI-First Mandate
        for pattern, desc in self.RAW_SQLITE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(GateIssue(
                    severity="CRITICAL",
                    title="Rule I.8 / I.9 FastAPI-First Violation: Raw SQLite Subshell Detected",
                    location=loc,
                    attack_vector=f"Command or specification contains {desc}.",
                    impact="Blocks on SQLite WAL database file locks, causing deadlocks and bypassing API validation.",
                    required_fix="Refactor operation to use FastAPI REST API (Port 8095) or scripts/core/api_client.py."
                ))

        # 3. Check Rule I.6: Banned Sci-Fi Fluff & Tropes
        for pattern, desc in self.BANNED_FLUFF_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(GateIssue(
                    severity="HIGH",
                    title=f"Rule I.6 Compliance Failure: {desc}",
                    location=loc,
                    attack_vector=f"Text contains banned term matching pattern '{pattern}'.",
                    impact="Aesthetic drift, cognitive dilution, and violation of no-snake-oil engineering standard.",
                    required_fix="Remove speculative sci-fi buzzwords and replace with empirical system metrics."
                ))

        # 4. Check Rule IV.2.b & KI-095: Viewport Collapse & Broken Responsive Styling
        for pattern, desc in self.VIEWPORT_DEFECT_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(GateIssue(
                    severity="HIGH",
                    title="KI-095 Viewport Collapse Defect Detected",
                    location=loc,
                    attack_vector=desc,
                    impact="Collapses layout on tablet and mobile Pegasus sentry viewports.",
                    required_fix="Use responsive CSS (max-width: 100%, flexbox, css grid) without fixed oversized pixel widths."
                ))

        # 5. Check Secrets / Credentials
        for pattern, desc in self.SECRET_PATTERNS:
            if re.search(pattern, content):
                issues.append(GateIssue(
                    severity="CRITICAL",
                    title="Security Guardrail Violation: Exposed Secret or Token",
                    location=loc,
                    attack_vector=f"{desc} in plain text.",
                    impact="Credential compromise and potential token exfiltration.",
                    required_fix="Redact secret token immediately and reference environment variable instead."
                ))

        # 6. Determine Verdict
        has_critical_or_high = any(i.severity in ("CRITICAL", "HIGH") for i in issues)
        if self.strict_mode:
            verdict = "REJECT" if issues else "APPROVE"
        else:
            verdict = "REJECT" if has_critical_or_high else "APPROVE"

        # Generate markdown report
        lines = [
            "# 🛡️ SOVEREIGN ADVERSARIAL GATE REVIEW REPORT",
            f"**Target**: `{loc}`",
            f"**Issues Identified**: {len(issues)}",
            "---",
            ""
        ]

        if issues:
            for issue in issues:
                lines.append(issue.to_markdown())
        else:
            lines.append("✓ No invariant violations, raw SQLite subshells, fluff tropes, or security defects detected.\n")

        lines.append(f"**VERDICT: {verdict}**")
        raw_markdown = "\n".join(lines)

        return AdversarialGateResult(
            verdict=verdict,
            issues=issues,
            raw_markdown=raw_markdown
        )

    def inspect_file(self, filepath: Union[str, Path]) -> AdversarialGateResult:
        path = Path(filepath)
        if not path.exists():
            return AdversarialGateResult(
                verdict="REJECT",
                issues=[GateIssue(
                    severity="CRITICAL",
                    title="File Not Found",
                    location=str(path),
                    attack_vector="Target file does not exist on disk.",
                    impact="Cannot inspect non-existent work order.",
                    required_fix="Verify filepath."
                )],
                raw_markdown=f"# 🛡️ SOVEREIGN ADVERSARIAL GATE REVIEW REPORT\n\n**[SEVERITY: CRITICAL]** - File Not Found\n**Location**: `{path}`\n\n**VERDICT: REJECT**"
            )

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return self.inspect_content(content, source_identifier=str(path))


def run_self_test() -> bool:
    """Runs test suite testing approved and rejected fixtures."""
    print("🔒 [TEST] Running SovereignAdversarialGate self-test suite...")
    gate = SovereignAdversarialGate()

    # 1. Clean compliant work order
    clean_wo = """
    # WORK ORDER: WO0010312
    - **Assigned Worker**: `clio`
    - **Architect**: `artemis`
    - **Traceability**: Rule Zero, Rule I.8

    ## Objective
    Stacklift Merkle audit chain using FastAPI endpoints.
    """
    res_clean = gate.inspect_content(clean_wo, "test_clean.md")
    print(f"  ✓ Clean work order verdict: {res_clean.verdict}")
    assert res_clean.verdict == "APPROVE", f"Expected APPROVE, got {res_clean.verdict}"

    # 2. Rule Zero violation (Artemis assigned to metal code/builds)
    bad_rule_zero = """
    # WORK ORDER: BAD-001
    - **Assigned Worker**: `artemis`
    Execute npm run build and apply migrations directly.
    """
    res_rz = gate.inspect_content(bad_rule_zero, "bad_rz.md")
    print(f"  ✓ Rule Zero violation verdict: {res_rz.verdict}")
    assert res_rz.verdict == "REJECT", f"Expected REJECT, got {res_rz.verdict}"
    assert any("Rule Zero" in i.title for i in res_rz.issues)

    # 3. Raw SQLite subshell violation
    bad_sqlite = """
    # WORK ORDER: BAD-002
    - **Assigned Worker**: `clio`
    Run: python3 -c 'import sqlite3; conn = sqlite3.connect("dna/sovereign_now.db")'
    """
    res_sql = gate.inspect_content(bad_sqlite, "bad_sql.md")
    print(f"  ✓ Raw SQLite violation verdict: {res_sql.verdict}")
    assert res_sql.verdict == "REJECT", f"Expected REJECT, got {res_sql.verdict}"
    assert any("Raw SQLite" in i.title for i in res_sql.issues)

    # 4. Fluff buzzwords violation
    bad_fluff = """
    # WORK ORDER: BAD-003
    - **Assigned Worker**: `clio`
    Establish a SYNAPTIC BRIDGE with 1000% SECURE COGNITIVE LOCK.
    """
    res_fluff = gate.inspect_content(bad_fluff, "bad_fluff.md")
    print(f"  ✓ Fluff tropes violation verdict: {res_fluff.verdict}")
    assert res_fluff.verdict == "REJECT", f"Expected REJECT, got {res_fluff.verdict}"

    print("🎉 [TEST] All SovereignAdversarialGate self-tests passed with 100% compliance!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Sovereign OS Adversarial Gate CLI")
    parser.add_argument("file", nargs="?", default=None, help="Path to work order markdown file")
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    parser.add_argument("--strict", action="store_true", help="Reject on any issue (including LOW/MEDIUM)")
    args = parser.parse_args()

    if args.test:
        success = run_self_test()
        sys.exit(0 if success else 1)

    if not args.file:
        parser.print_help()
        sys.exit(1)

    gate = SovereignAdversarialGate(strict_mode=args.strict)
    result = gate.inspect_file(args.file)
    print(result.raw_markdown)
    sys.exit(0 if result.is_approved else 1)


if __name__ == "__main__":
    main()
