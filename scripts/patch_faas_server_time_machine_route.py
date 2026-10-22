#!/home/james/stacklabs/.venv/bin/python3
"""
Idempotent router mounter wiring faas_time_machine_bp into scripts/faas_server.py (WO0011280).
Enforces Argon Law 8 (Zero Orphan Blueprints) and guards against corrupting FastAPI constructor parameters.
"""
from __future__ import annotations

import os
from pathlib import Path

FAAS_SERVER_PATH = Path("/home/james/stacklabs/scripts/faas_server.py")
ROUTER_CHECK = "faas_time_machine_router"
MOUNT_BLOCK = """
# Mount FaaS Time Machine Blueprint (WO0011280)
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.faas_time_machine_bp import router as faas_time_machine_router
    app.include_router(faas_time_machine_router)
    logger.info("Mounted FaaS Time Machine router on /api/snipe/{id}/time_machine")
except Exception as e:
    logger.error(f"Failed to mount faas_time_machine_router: {e}")
"""


def patch_faas_server() -> bool:
    if not FAAS_SERVER_PATH.exists():
        raise FileNotFoundError(f"Missing target server file: {FAAS_SERVER_PATH}")

    original = FAAS_SERVER_PATH.read_text(encoding="utf-8")
    if ROUTER_CHECK in original:
        print("faas_server.py already mounts faas_time_machine_router (idempotent no-op).")
        return False

    lines = original.splitlines()
    
    # Locate the last app.include_router call to safely append without interrupting app = FastAPI(...)
    last_include_idx = -1
    for idx, line in enumerate(lines):
        if "app.include_router(" in line:
            last_include_idx = idx

    if last_include_idx != -1:
        # Seek past any trailing except/logger lines in that block
        insert_idx = last_include_idx + 1
        while insert_idx < len(lines) and (
            lines[insert_idx].strip().startswith("except")
            or lines[insert_idx].strip().startswith("logger.")
            or lines[insert_idx].strip().startswith("pass")
            or not lines[insert_idx].strip()
        ):
            insert_idx += 1
        new_lines = lines[:insert_idx] + MOUNT_BLOCK.strip().splitlines() + [""] + lines[insert_idx:]
    else:
        new_lines = lines + [""] + MOUNT_BLOCK.strip().splitlines()

    updated = "\n".join(new_lines) + "\n"
    tmp_path = FAAS_SERVER_PATH.with_suffix(".py.tmp")
    tmp_path.write_text(updated, encoding="utf-8")
    os.replace(tmp_path, FAAS_SERVER_PATH)
    print("Successfully and safely wired faas_time_machine_router into scripts/faas_server.py.")
    return True


if __name__ == "__main__":
    patch_faas_server()
