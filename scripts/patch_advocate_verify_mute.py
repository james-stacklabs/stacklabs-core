#!/home/james/stacklabs/.venv/bin/python3
"""
Patch all advocate verify.sh scripts to enforce DISCORD_MUTE.lock
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/patch_advocate_verify_mute.py
"""
import pathlib
import sys

ROOT_DIR = pathlib.Path("/home/james/stacklabs")
ADVOCATE_DIR = ROOT_DIR / "vfs" / "advocates"
BRIDGE_VERIFY = ROOT_DIR / "vfs" / "services" / "chat_velocity_bridge" / "verify.sh"

MUTE_SNIPPET = """
# Master Stigmergic Mute Check
if [[ -f "/home/james/stacklabs/vfs/.state/DISCORD_MUTE.lock" ]]; then
    exit 0
fi
"""


def patch_script(script_path: pathlib.Path) -> bool:
    if not script_path.exists():
        return False
    content = script_path.read_text(encoding="utf-8")
    if "DISCORD_MUTE.lock" in content:
        print(f"Already patched: {script_path.relative_to(ROOT_DIR)}")
        return True

    # Insert right after set -euo pipefail
    lines = content.splitlines()
    insert_idx = 1
    for i, line in enumerate(lines):
        if "set -euo pipefail" in line or "mkdir -p" in line:
            insert_idx = i + 1

    lines.insert(insert_idx, MUTE_SNIPPET.strip())
    new_content = "\n".join(lines) + "\n"
    script_path.write_text(new_content, encoding="utf-8")
    print(f"✓ Patched mute check into: {script_path.relative_to(ROOT_DIR)}")
    return True


def main() -> int:
    patched_count = 0
    if ADVOCATE_DIR.exists():
        for adv in ADVOCATE_DIR.iterdir():
            if adv.is_dir() and (adv / "verify.sh").exists():
                if patch_script(adv / "verify.sh"):
                    patched_count += 1

    if BRIDGE_VERIFY.exists():
        if patch_script(BRIDGE_VERIFY):
            patched_count += 1

    print(f"Total verify.sh scripts patched with master mute check: {patched_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
