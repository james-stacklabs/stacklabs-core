#!/home/james/stacklabs/.venv/bin/python3
"""
Deployment script for WO0011176: ServiceNow Merkle Delta Sync Engine.
Installs validated drop-in script from pilot_drops/downloads/scratch/ into scripts/.
"""

import os
import pathlib
import shutil
import subprocess
import sys

SCRATCH_SOURCE = pathlib.Path(
    "/home/james/stacklabs/pilot_drops/downloads/scratch/servicenow_sync_engine.py"
)
TARGET_SCRIPT = pathlib.Path(
    "/home/james/stacklabs/scripts/servicenow_sync_engine.py"
)
VENV_PYTHON = "/home/james/stacklabs/.venv/bin/python3"


def deploy() -> None:
    print("[WO0011176] Starting ServiceNow Merkle Delta Sync Engine deployment...")

    if not SCRATCH_SOURCE.exists():
        print(f"❌ Error: Source file not found: {SCRATCH_SOURCE}")
        sys.exit(1)

    # 1. Install to canonical scripts directory
    shutil.copy2(SCRATCH_SOURCE, TARGET_SCRIPT)
    TARGET_SCRIPT.chmod(0o755)
    print(f"  ✔ Deployed {TARGET_SCRIPT} (755)")

    # 2. Syntax check
    res = subprocess.run(
        [VENV_PYTHON, "-m", "py_compile", str(TARGET_SCRIPT)],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(f"❌ Syntax error in {TARGET_SCRIPT}:\n{res.stderr}")
        sys.exit(1)
    print("  ✔ PyCompile syntax validation passed cleanly.")

    # 3. Anti-metaphor linter gate
    linter_path = "/home/james/stacklabs/scripts/anti_metaphor_linter.py"
    if os.path.exists(linter_path):
        res = subprocess.run(
            [VENV_PYTHON, linter_path, "--artifacts", str(TARGET_SCRIPT)],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            print(f"❌ Anti-metaphor lint failed:\n{res.stdout}\n{res.stderr}")
            sys.exit(1)
        print("  ✔ Anti-metaphor linter gate passed cleanly.")

    # 4. CLI dry-run verification
    res = subprocess.run(
        [VENV_PYTHON, str(TARGET_SCRIPT), "--dry-run"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(f"❌ Dry-run execution failed:\n{res.stderr}")
        sys.exit(1)
    print("  ✔ Merkle delta dry-run verified successfully:")
    print(res.stdout.strip())

    print("\n[WO0011176] Deployment completed successfully.")


if __name__ == "__main__":
    deploy()
