#!/home/james/stacklabs/.venv/bin/python3
"""
Clean-Room Legacy Workflows Archival Script.
Moves .agents/workflows/ into pilot_drops/archives/legacy_workflows_{TIMESTAMP}/
and removes the legacy directory to complete Antigravity Skills cutover.
"""

import pathlib
import shutil
import sys
from datetime import datetime

STACKLABS_ROOT = pathlib.Path("/home/james/stacklabs")
WORKFLOWS_DIR = STACKLABS_ROOT / ".agents" / "workflows"
ARCHIVES_ROOT = STACKLABS_ROOT / "pilot_drops" / "archives"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ARCHIVE_DEST = ARCHIVES_ROOT / f"legacy_workflows_{TIMESTAMP}"

def main() -> int:
    if not WORKFLOWS_DIR.exists():
        print(f"[INFO] Legacy workflows directory does not exist: {WORKFLOWS_DIR}")
        return 0

    wf_files = list(WORKFLOWS_DIR.glob("*.md"))
    print(f"[INFO] Found {len(wf_files)} legacy workflow file(s) in {WORKFLOWS_DIR}")

    ARCHIVE_DEST.mkdir(parents=True, exist_ok=True)
    for wf in wf_files:
        dest_file = ARCHIVE_DEST / wf.name
        shutil.copy2(wf, dest_file)
        wf.unlink()

    # Remove legacy directory if empty
    try:
        shutil.rmtree(WORKFLOWS_DIR)
        print(f"[PASS] Successfully archived workflows to {ARCHIVE_DEST} and removed {WORKFLOWS_DIR}")
    except Exception as exc:
        print(f"[WARN] Error removing {WORKFLOWS_DIR}: {exc}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
