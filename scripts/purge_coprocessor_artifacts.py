#!/usr/bin/env python3
"""
StackLabs Enterprise Nomenclature Cleanser: Purge Cyberpunk Reflex Coprocessor Slop
Governed by: Invariant 38.1 (The Ripperdoc Invariant) & WO0011054
Target: Purges all traces of 'Reflex Coprocessor' from sprint artifacts, whitepapers, scripts, and chronicles.
"""

import os
import sys
import re
from pathlib import Path

BASE_DIR = Path("/home/james/stacklabs")

REPLACEMENTS = [
    # Specific compound terms first
    (re.compile(r'L1 Reflex Coprocessor', re.IGNORECASE), "Edge Execution Appliance"),
    (re.compile(r'Reflex Coprocessor', re.IGNORECASE), "Edge Execution Appliance"),
    (re.compile(r'reflex co-processor', re.IGNORECASE), "edge execution appliance"),
    (re.compile(r'symbiotic coprocessor', re.IGNORECASE), "asynchronous edge state cache"),
    (re.compile(r'Symbiotic Coprocessor', re.IGNORECASE), "Asynchronous Edge State Cache"),
    (re.compile(r'\[StackLabs Reflex Coprocessor\]', re.IGNORECASE), "[StackLabs In-Memory VFS]"),
    (re.compile(r'real-time reflex engine', re.IGNORECASE), "in-memory execution engine"),
    (re.compile(r'Real-Time Reflex Engine', re.IGNORECASE), "In-Memory Execution Engine"),
    (re.compile(r'real-time reflex', re.IGNORECASE), "deterministic microsecond execution"),
    (re.compile(r'Real-Time Reflex', re.IGNORECASE), "Deterministic Microsecond Execution"),
    (re.compile(r'L1 Reflex Cache', re.IGNORECASE), "In-Memory Edge State Cache"),
    (re.compile(r'l1 reflex cache', re.IGNORECASE), "in-memory edge state cache"),
    (re.compile(r'L1 Reflex', re.IGNORECASE), "Edge Execution Layer"),
    (re.compile(r'l1 reflex', re.IGNORECASE), "edge execution layer"),
    (re.compile(r'Reflex Architecture', re.IGNORECASE), "Edge Execution Architecture"),
    (re.compile(r'reflex architecture', re.IGNORECASE), "edge execution architecture"),
    (re.compile(r'Clio metal', re.IGNORECASE), "local x86_64 Linux"),
    (re.compile(r'Clio Forge Master', re.IGNORECASE), "Autonomous Execution Worker"),
    (re.compile(r'clio forge', re.IGNORECASE), "autonomous execution worker"),
    (re.compile(r'Invariant 0 \(Rule Zero\)', re.IGNORECASE), "Invariant 0 (Division of Labor)"),
    (re.compile(r'Rule Zero', re.IGNORECASE), "Foundational Operating Principle"),
    (re.compile(r'rule zero', re.IGNORECASE), "foundational operating principle"),
    (re.compile(r'Invariant 0:', re.IGNORECASE), "Core Invariant:"),
    (re.compile(r'\bInvariant 0\b', re.IGNORECASE), "Core Invariant"),
    (re.compile(r'http://100\.108\.185\.53:8088', re.IGNORECASE), "http://artemis.local:8088"),
    (re.compile(r' / `100\.108\.185\.53`', re.IGNORECASE), ""),
    (re.compile(r' \(`100\.108\.185\.53`\)', re.IGNORECASE), ""),
    (re.compile(r'`100\.108\.185\.53`', re.IGNORECASE), "Artemis node"),
    (re.compile(r', Port 3033\)', re.IGNORECASE), ")"),
    (re.compile(r' on Port 3033\b', re.IGNORECASE), ""),
]

def clean_file(file_path: Path) -> bool:
    if not file_path.exists():
        return False
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        print(f"  ❌ Error reading {file_path}: {e}")
        return False

    modified = content
    for pattern, replacement in REPLACEMENTS:
        modified = pattern.sub(replacement, modified)

    if modified != content:
        file_path.write_text(modified, encoding='utf-8')
        print(f"  ✔ Scrubbed: {file_path.relative_to(BASE_DIR) if file_path.is_relative_to(BASE_DIR) else file_path}")
        return True
    return False

def main():
    print("=" * 80)
    print("🧹 STACKLABS PURGE ENGINE: EXECUTING INVARIANT 38.1 NOMENCLATURE CLEANSE")
    print("=" * 80)

    # 1. Rename 00_EXECUTIVE_WHITE_PAPER_THE_L1_REFLEX_COPROCESSOR.md
    sprint_dir = BASE_DIR / "artifacts" / "sprints" / "daily_sprint_2026_10_10"
    old_whitepaper = sprint_dir / "00_EXECUTIVE_WHITE_PAPER_THE_L1_REFLEX_COPROCESSOR.md"
    new_whitepaper = sprint_dir / "00_EXECUTIVE_WHITE_PAPER_THE_EDGE_EXECUTION_APPLIANCE.md"

    if old_whitepaper.exists():
        old_whitepaper.rename(new_whitepaper)
        print(f"  ✔ Renamed whitepaper: {new_whitepaper.name}")

    # Remove stale docx with old names
    stale_docx = [
        sprint_dir / "00_EXECUTIVE_WHITE_PAPER_THE_L1_REFLEX_COPROCESSOR.md.docx",
        sprint_dir / "06_VFS_CMDB_SERVICENOW_BENCHMARK_AND_IN_MEMORY_REFLEX_TRANSCRIPT.md.docx",
    ]
    for d in stale_docx:
        if d.exists():
            d.unlink()
            print(f"  ✔ Deleted stale binary docx: {d.name}")

    # 2. Clean all markdown files in daily_sprint_2026_10_10
    if sprint_dir.exists():
        for p in sprint_dir.glob("*.md"):
            clean_file(p)

    # 3. Clean studio_coprocessor_oct10 reports & transcripts
    studio_dir = BASE_DIR / "artifacts" / "studio_coprocessor_oct10"
    if studio_dir.exists():
        old_spec = studio_dir / "Reports" / "01-L1 Reflex Coprocessor Enterprise Technical Architecture Specification.md"
        new_spec = studio_dir / "Reports" / "01-Edge Execution Appliance Enterprise Technical Architecture Specification.md"
        if old_spec.exists():
            old_spec.rename(new_spec)
            print(f"  ✔ Renamed studio spec: {new_spec.name}")

        for p in studio_dir.rglob("*.md"):
            clean_file(p)
        for p in studio_dir.rglob("*.csv"):
            clean_file(p)

    # 4. Clean active scripts & frontends
    active_code_files = [
        BASE_DIR / "scripts" / "blueprints" / "cmdb_benchmark_api.py",
        BASE_DIR / "scripts" / "colab_qwen25_slm_server.py",
        BASE_DIR / "scripts" / "sync_pilot_passport.py",
        BASE_DIR / "apps" / "horizon_scratchpad" / "passport.html",
        Path("/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/epoch_sources/SESSION_CHRONICLE_CURRENT_WEEK.md"),
    ]
    for p in active_code_files:
        clean_file(p)

    print("🟢 Scrub pass complete.")

if __name__ == "__main__":
    main()
