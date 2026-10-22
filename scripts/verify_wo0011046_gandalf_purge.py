#!/usr/bin/env python3
"""
Verification Script for WO0011046: Gandalf UI Craft & Invariant 38 Slop Metaphor Purge
"""
import sys
from pathlib import Path

CMDB_DIR = Path("/home/james/stacklabs/apps/cmdb_studio/src")
BANNED_STRINGS = [
    "Best Buy",
    "Pepe Silvia",
    "Port 3025",
    "100.96.77.20",
    "[DUAL-RUNNER]",
    "[L1 REFLEX METAL]",
    "[WAN REST]"
]

def scan_for_slop():
    violations = []
    for f in CMDB_DIR.rglob("*.tsx"):
        content = f.read_text(encoding="utf-8")
        for banned in BANNED_STRINGS:
            if banned in content:
                violations.append((str(f), banned))
                
    if violations:
        for file_path, banned in violations:
            print(f"❌ SLOP DETECTED in {file_path}: '{banned}'")
        sys.exit(1)
        
    print("✅ ZERO SLOP DETECTED: All chat metaphors, leaked ports, and bracket badges completely purged.")
    sys.exit(0)

if __name__ == "__main__":
    scan_for_slop()
