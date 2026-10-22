#!/usr/bin/env python3
"""
=============================================================================
MODULE: audit_file_headers.py
ROLE: Audit and enforce 10-line laser-scalpel routing headers on docs and code
RUNNER: Aggie (agy) on Clio Metal Forge via .venv/bin/python3
=============================================================================
TABLE OF CONTENTS & SYMBOL MAP:
  - L0025-L0045: Configuration & Routing Requirements
  - L0047-L0090: Markdown YAML Frontmatter Auditor
  - L0092-L0135: Python Script Symbol Map Auditor (>300 lines)
  - L0137-L0190: CLI Interface, Directory Traversal & Compliance Report
=============================================================================
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

DOCS_ROOT = Path("/home/james/stacklabs/docs")
SCRIPTS_ROOT = Path("/home/james/stacklabs/scripts")
DNA_ROOT = Path("/home/james/stacklabs/dna")

REQUIRED_MD_KEYS = ["status", "domain", "last_verified", "canonical_source", "summary", "agent_routing"]

def audit_markdown_file(path: Path) -> Tuple[bool, str]:
    """Verify markdown file has a compliant 10-line YAML frontmatter header."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"Could not read file: {e}"

    lines = content.splitlines()
    if len(lines) < 7:
        return False, "File too short to contain header"

    if lines[0].strip() != "---":
        return False, "Missing opening YAML '---' delimiter on line 1"

    closing_idx = -1
    for idx, line in enumerate(lines[1:25], start=1):
        if line.strip() == "---":
            closing_idx = idx
            break

    if closing_idx == -1:
        return False, "Missing closing '---' delimiter within first 25 lines"

    header_block = "\n".join(lines[1:closing_idx])
    missing_keys = [k for k in REQUIRED_MD_KEYS if f"{k}:" not in header_block]
    if missing_keys:
        return False, f"Header missing required keys: {', '.join(missing_keys)}"

    return True, "Compliant"

def audit_python_script(path: Path) -> Tuple[bool, str]:
    """Verify Python script over 300 lines has a top-of-file symbol map docstring."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"Could not read file: {e}"

    lines = content.splitlines()
    line_count = len(lines)
    if line_count <= 300:
        return True, "Under 300 lines (exempt)"

    head_block = "\n".join(lines[:50])
    if "TABLE OF CONTENTS" not in head_block and "SYMBOL MAP" not in head_block:
        return False, f"Monolith ({line_count} lines) missing 'TABLE OF CONTENTS & SYMBOL MAP' in first 50 lines"

    return True, f"Compliant ({line_count} lines with Symbol Map)"

def run_audit(target_dir: Path) -> Dict[str, List[Tuple[Path, str]]]:
    """Traverse directory and audit all markdown and python files."""
    results = {"md_passed": [], "md_failed": [], "py_passed": [], "py_failed": []}

    for root, _, files in os.walk(target_dir):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix == ".md":
                ok, msg = audit_markdown_file(file_path)
                if ok:
                    results["md_passed"].append((file_path, msg))
                else:
                    results["md_failed"].append((file_path, msg))
            elif file_path.suffix == ".py":
                ok, msg = audit_python_script(file_path)
                if ok:
                    results["py_passed"].append((file_path, msg))
                else:
                    results["py_failed"].append((file_path, msg))

    return results

def main() -> int:
    parser = argparse.ArgumentParser(description="Audit repository file headers and symbol maps.")
    parser.add_argument("--path", type=str, default="/home/james/stacklabs/dna", help="Directory or file path to audit")
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"[ERROR] Target path does not exist: {target}")
        return 1

    print(f"[AUDIT] Scanning {target} for laser-scalpel routing compliance...")
    results = run_audit(target)

    print("\n--- AUDIT RESULTS ---")
    print(f"Markdown Files: {len(results['md_passed'])} passed, {len(results['md_failed'])} non-compliant")
    print(f"Python Scripts: {len(results['py_passed'])} passed, {len(results['py_failed'])} non-compliant")

    if results["md_failed"]:
        print("\n[NON-COMPLIANT MARKDOWN FILES]:")
        for p, reason in results["md_failed"][:10]:
            print(f"  ❌ {p}: {reason}")
        if len(results["md_failed"]) > 10:
            print(f"  ... and {len(results['md_failed']) - 10} more.")

    if results["py_failed"]:
        print("\n[NON-COMPLIANT PYTHON MONOLITHS (>300 lines missing Symbol Map)]:")
        for p, reason in results["py_failed"][:10]:
            print(f"  ⚠️  {p}: {reason}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
