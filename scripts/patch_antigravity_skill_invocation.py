#!/home/james/stacklabs/.venv/bin/python3
"""
Patch Antigravity Skill Invocation Script.
Harmonizes all active resume generators and skill documentation to use
the canonical hyphenated skill command /stacklabs-boot ahead of the October 19 deprecation.
"""

import pathlib
import sys

STACKLABS_ROOT = pathlib.Path("/home/james/stacklabs")
LEGACY_CMD = "".join(["/stacklabs", "_boot"])
CANONICAL_CMD = "/stacklabs-boot"

TARGET_FILES = [
    STACKLABS_ROOT / "scripts" / "sync_pilot_passport.py",
    STACKLABS_ROOT / "scripts" / "compile_argon_skills.py",
    STACKLABS_ROOT / ".agents" / "skills" / "stacklabs-sync" / "scripts" / "unified_sync.py",
    STACKLABS_ROOT / ".agents" / "skills" / "stacklabs-sync" / "SKILL.md",
    STACKLABS_ROOT / ".agents" / "skills" / "stacklabs-boot" / "SKILL.md",
    STACKLABS_ROOT / "pilot_drops" / "PILOT_PASSPORT_CURRENT.md",
]


def patch_file(path: pathlib.Path) -> int:
    if not path.exists():
        print(f"[-] File not found: {path}")
        return 0

    original = path.read_text(encoding="utf-8")
    count = original.count(LEGACY_CMD)
    if count == 0:
        print(f"[*] No occurrences of {LEGACY_CMD} in {path.name}")
        return 0

    updated = original.replace(LEGACY_CMD, CANONICAL_CMD)
    path.write_text(updated, encoding="utf-8")
    print(f"[+] Patched {count} occurrence(s) in {path.relative_to(STACKLABS_ROOT)}")
    return count


def main() -> int:
    total_patched = 0
    for target in TARGET_FILES:
        total_patched += patch_file(target)

    print(f"\n[+] Total occurrences patched across {len(TARGET_FILES)} files: {total_patched}")
    if total_patched == 0:
        print("[-] Warning: No files modified. Review target patterns.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
