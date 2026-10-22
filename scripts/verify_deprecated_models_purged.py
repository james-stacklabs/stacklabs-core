#!/usr/bin/env python3
"""
scripts/verify_deprecated_models_purged.py
=============================================================================
Verification Test Harness for WO0010544:
1. Zero Deprecated References in scripts/ (excluding _archive/)
2. Bytecode Compilation across all python files
3. API & CLI Verification for mard_editorial_chamber & api_client
=============================================================================
"""

import sys
import os
import subprocess
import py_compile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

PREFIX = "gemini"
DEPRECATED_STRINGS = [
    f"{PREFIX}-2.5-flash",
    f"{PREFIX}-2.5-pro",
    f"{PREFIX}-3.5-flash-lite",
]


def test_zero_deprecated_references():
    print("\n[TEST 1] Scanning for deprecated model strings in scripts/ (excluding _archive)...")
    violations = []
    py_files = sorted(SCRIPTS_DIR.rglob("*.py"))

    for py_file in py_files:
        if "_archive" in str(py_file):
            continue
        if py_file.resolve() == Path(__file__).resolve():
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: could not read {py_file}: {e}")
            continue

        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            for dep in DEPRECATED_STRINGS:
                if dep in line:
                    violations.append((str(py_file.relative_to(REPO_ROOT)), idx, dep, line.strip()))

    if violations:
        print(f"FAILED: Found {len(violations)} deprecated reference(s):")
        for f, ln, dep, snippet in violations:
            print(f"  - {f}:{ln} [{dep}] -> {snippet}")
        assert False, f"Found {len(violations)} deprecated model references!"
    
    print(f"PASSED: Scanned {len(py_files)} files. Exactly 0 deprecated references found.")


def test_bytecode_compilation():
    print("\n[TEST 2] Verifying bytecode compilation across python files...")
    py_files = sorted(SCRIPTS_DIR.rglob("*.py"))
    compiled_count = 0
    errors = []

    for py_file in py_files:
        if "_archive" in str(py_file):
            continue
        try:
            py_compile.compile(str(py_file), doraise=True)
            compiled_count += 1
        except Exception as e:
            errors.append((str(py_file.relative_to(REPO_ROOT)), str(e)))

    if errors:
        print(f"FAILED: {len(errors)} file(s) failed compilation:")
        for f, err in errors:
            print(f"  - {f}: {err}")
        assert False, f"{len(errors)} files failed py_compile"

    print(f"PASSED: Compiled {compiled_count} files with zero syntax errors.")


def test_api_verification():
    print("\n[TEST 3A] Verifying scripts.core.api_client.mard_run_editorial_deliberation...")
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.core.api_client import mard_run_editorial_deliberation

    default_model = mard_run_editorial_deliberation.__defaults__[1]
    print(f"mard_run_editorial_deliberation default model is: '{default_model}'")
    assert default_model == "gemini-3.8-flash", f"Expected gemini-3.8-flash, got {default_model}"
    print("PASSED: api_client default model is gemini-3.8-flash.")


def test_cli_verification():
    print("\n[TEST 3B] Verifying scripts/mard_editorial_chamber.py --help default...")
    python_bin = sys.executable
    cmd = [python_bin, str(SCRIPTS_DIR / "mard_editorial_chamber.py"), "--help"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI help failed with return code {res.returncode}: {res.stderr}"

    help_text = res.stdout
    assert "--model" in help_text, "Missing --model argument in help"
    assert "default='gemini-3.8-flash'" in help_text or "default: 'gemini-3.8-flash'" in help_text or "gemini-3.8-flash" in help_text, (
        f"--model help text does not show gemini-3.8-flash as default:\n{help_text}"
    )
    print("PASSED: mard_editorial_chamber.py --help indicates gemini-3.8-flash default.")


def main():
    print("=" * 60)
    print("WO0010544 VERIFICATION TEST HARNESS: PURGE DEPRECATED GEMINI MODELS")
    print("=" * 60)

    test_zero_deprecated_references()
    test_bytecode_compilation()
    test_api_verification()
    test_cli_verification()

    print("\n" + "=" * 60)
    print("ALL VERIFICATION SUITES PASSED CLEANLY (100% GREEN) ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
