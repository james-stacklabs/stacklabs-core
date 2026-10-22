#!/usr/bin/env python3
"""
StackLabs Cyberpunk & Cyberware Slop Verification Gate
Path: /home/james/stacklabs/scripts/verify_cyberpunk_slop_purge.py
Invariants: 15, 26, 32, 38
"""
import sys
from pathlib import Path

TARGETS = [
    Path("/home/james/stacklabs/dossiers/07_Optimum_Healthcare_Cherlyn/CHERLYN_SERVICENOW_BATTLE_CARD.md"),
    Path("/home/james/stacklabs/apps/cmdb_studio/src/components/LiveShootoutArenaView.tsx"),
    Path("/home/james/stacklabs/scripts/anti_metaphor_linter.py"),
    Path("/home/james/stacklabs/.agents/rules/07_FRONTEND_CRAFT_AND_ANTI_SLOP.md"),
]

BANNED_STRINGS = [
    "reflex coprocessor",
    "reflex co-processor",
    "l1 reflex",
    "l1 coprocessor",
    "spinal cord",
    "symbiotic coprocessor",
    "eurobucks",
    "ripperdoc",
    "humanity loss",
]

def verify_purge():
    print("================================================================================")
    print("  STACKLABS VERIFICATION GATE: CYBERPUNK 2020/RED CYBERWARE SLOP PURGE")
    print("================================================================================")

    # 1. Verify linter and rules have the denylist
    linter_text = Path("/home/james/stacklabs/scripts/anti_metaphor_linter.py").read_text(encoding="utf-8")
    if "reflex coprocessor" in linter_text and "eurobucks" in linter_text and "ripperdoc" in linter_text:
        print("  [PASS] anti_metaphor_linter.py contains Cyberpunk RPG denylist.")
    else:
        print("  [FAIL] anti_metaphor_linter.py missing Cyberpunk RPG denylist.")
        sys.exit(1)

    rules_text = Path("/home/james/stacklabs/.agents/rules/07_FRONTEND_CRAFT_AND_ANTI_SLOP.md").read_text(encoding="utf-8")
    if "Ripperdoc Invariant" in rules_text:
        print("  [PASS] 07_FRONTEND_CRAFT_AND_ANTI_SLOP.md contains Ripperdoc Invariant.")
    else:
        print("  [FAIL] 07_FRONTEND_CRAFT_AND_ANTI_SLOP.md missing Ripperdoc Invariant.")
        sys.exit(1)

    # 2. Check active production targets for banned strings
    clean_targets = [
        Path("/home/james/stacklabs/dossiers/07_Optimum_Healthcare_Cherlyn/CHERLYN_SERVICENOW_BATTLE_CARD.md"),
        Path("/home/james/stacklabs/apps/cmdb_studio/src/components/LiveShootoutArenaView.tsx"),
    ]

    failures = []
    for target in clean_targets:
        if not target.exists():
            print(f"  [FAIL] Target missing: {target}")
            failures.append(str(target))
            continue
            
        content = target.read_text(encoding="utf-8").lower()
        for banned in BANNED_STRINGS:
            if banned in content:
                print(f"  [FAIL] {target.name} contains banned Cyberpunk string: '{banned}'")
                failures.append(f"{target.name}: {banned}")
            else:
                print(f"  [PASS] {target.name} is clean of '{banned}'")

    if failures:
        print(f"\nVerification FAILED with {len(failures)} slop violations.")
        sys.exit(1)

    print("\nAll Cyberpunk Slop Purge checks PASSED cleanly. 0 Eurobucks, 0 Humanity Loss.")
    sys.exit(0)

if __name__ == "__main__":
    verify_purge()
