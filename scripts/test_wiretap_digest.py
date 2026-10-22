#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Bleacher Wiretap Digest Test Harness
Validates that:
1. bleacher_wiretap_digest.py compiles cleanly.
2. --dry-run extracts real quotes and returns structured JSON with zero errors.
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/test_wiretap_digest.py
"""
import json
import pathlib
import subprocess
import sys

PROJECT_ROOT = pathlib.Path("/home/james/stacklabs")
PYTHON_EXEC = PROJECT_ROOT / ".venv" / "bin" / "python3"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "bleacher_wiretap_digest.py"


def test_dry_run():
    print("Testing bleacher_wiretap_digest.py --dry-run...")
    cmd = [str(PYTHON_EXEC), str(SCRIPT_PATH), "--dry-run"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    data = json.loads(res.stdout)
    assert "headline" in data, "Digest output missing 'headline'"
    assert "featured_quotes" in data and len(data["featured_quotes"]) > 0, "No featured quotes returned"
    assert "barf_reaction" in data, "Digest output missing 'barf_reaction'"
    
    print(f"  ✓ Digest headline: {data['headline']}")
    print(f"  ✓ Featured quotes count: {len(data['featured_quotes'])}")
    print(f"  ✓ Barf reaction: {data['barf_reaction'][:80]}...")


def main():
    print("==================================================")
    print("⚡ STACKLABS BLEACHER WIRETAP DIGEST TEST HARNESS")
    print("==================================================")
    test_dry_run()
    print("\n✅ WIRETAP DIGEST HARNESS PASSED.")


if __name__ == "__main__":
    main()
