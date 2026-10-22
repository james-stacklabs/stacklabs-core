#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Atomic Patch: sync_to_gdrive.sh Wildcard Markdown & Scratch Hygiene
Ticket: WO0011211
Author: James Carroll (Pilot) & Lead Systems Architect
"""
import os
import sys
import shutil
from pathlib import Path

SYNC_SCRIPT = Path("/home/james/stacklabs/scripts/sync_to_gdrive.sh")
SCRATCH_DIR = Path("/home/james/stacklabs/pilot_drops/downloads/scratch")


def patch_sync_script() -> bool:
    if not SYNC_SCRIPT.exists():
        print(f"ERROR: {SYNC_SCRIPT} not found.", file=sys.stderr)
        return False

    content = SYNC_SCRIPT.read_text(encoding="utf-8")

    # Target Section 2A block
    old_block_pattern = (
        '# A. Pilot drops (Passport & Scratchpad)\n'
        'rclone copyto "/home/james/stacklabs/pilot_drops/PILOT_PASSPORT_CURRENT.md" "stacklabs_edge:pilot_drops/PILOT_PASSPORT_CURRENT.md" --timeout 25s --contimeout 10s --no-traverse --quiet &\n'
        'PID_PASS=$!\n'
        'rclone copyto "/home/james/stacklabs/pilot_drops/scratch_pad.md" "stacklabs_edge:pilot_drops/scratch_pad.md" --timeout 25s --contimeout 10s --no-traverse --quiet &\n'
        'PID_PAD=$!'
    )

    new_block = (
        '# A. Pilot drops (All active standalone markdown dossiers & scratchpads)\n'
        'rclone copy "/home/james/stacklabs/pilot_drops" "stacklabs_edge:pilot_drops" \\\n'
        '  --timeout 25s --contimeout 10s \\\n'
        '  --filter "+ *.md" \\\n'
        '  --filter "- *" \\\n'
        '  --max-depth 1 \\\n'
        '  --copy-links \\\n'
        '  --fast-list \\\n'
        '  --quiet &\n'
        'PID_PASS=$!\n'
        'PID_PAD=""'
    )

    if old_block_pattern in content:
        content = content.replace(old_block_pattern, new_block, 1)
        SYNC_SCRIPT.write_text(content, encoding="utf-8")
        print(f"[OK] Successfully patched Section 2A in {SYNC_SCRIPT}")
        return True
    elif 'filter "+ *.md"' in content and "PID_PAD=\"\"" in content:
        print(f"[INFO] Section 2A in {SYNC_SCRIPT} is already patched.")
        return True
    else:
        print("[ERROR] Could not match target Section 2A block in sync_to_gdrive.sh.", file=sys.stderr)
        return False


def clean_scratch_directory() -> bool:
    if not SCRATCH_DIR.exists():
        print(f"[WARN] Scratch directory {SCRATCH_DIR} does not exist. Creating it.")
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        return True

    archive_target = SCRATCH_DIR / "archive" / "20261017_cleanup"
    archive_target.mkdir(parents=True, exist_ok=True)

    # Remove __pycache__ if present
    pycache = SCRATCH_DIR / "__pycache__"
    if pycache.exists():
        shutil.rmtree(pycache)
        print("[OK] Removed stale __pycache__ directory.")

    moved_count = 0
    for item in list(SCRATCH_DIR.iterdir()):
        if item.name == "archive":
            continue
        dest = archive_target / item.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        shutil.move(str(item), str(dest))
        moved_count += 1

    print(f"[OK] Archived {moved_count} legacy artifacts to {archive_target}")
    return True


def main() -> int:
    ok_sync = patch_sync_script()
    ok_clean = clean_scratch_directory()

    if ok_sync and ok_clean:
        print("[SUCCESS] All WO0011211 patch operations succeeded.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
