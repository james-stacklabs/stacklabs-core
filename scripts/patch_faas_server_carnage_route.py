#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011237: Surgical patch script to mount faas_carnage_telemetry router in scripts/faas_server.py.
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
"""

import sys
from pathlib import Path

FAAS_SERVER_PATH = Path("/home/james/stacklabs/scripts/faas_server.py")


def patch_faas_server() -> int:
    if not FAAS_SERVER_PATH.exists():
        print(f"[ERROR] faas_server.py not found at {FAAS_SERVER_PATH}", file=sys.stderr)
        return 1

    content = FAAS_SERVER_PATH.read_text(encoding="utf-8")
    mount_marker = "from scripts.blueprints.faas_carnage_telemetry import router as carnage_router"

    if mount_marker in content:
        print("[INFO] faas_carnage_telemetry router already mounted in faas_server.py. Skipping.")
        return 0

    target = "app.include_router(faas_lexicon_router)"
    if target not in content:
        print("[ERROR] Could not find target mount point in faas_server.py", file=sys.stderr)
        return 1

    replacement = (
        "app.include_router(faas_lexicon_router)\n"
        "    try:\n"
        "        from scripts.blueprints.faas_carnage_telemetry import router as carnage_router\n"
        "        app.include_router(carnage_router)\n"
        "        logger.info(\"Mounted CFB Carnage Telemetry router on /api/faas/cfb\")\n"
        "    except Exception as e:\n"
        "        logger.error(f\"Failed to mount carnage_router: {e}\")"
    )

    new_content = content.replace(target, replacement, 1)
    FAAS_SERVER_PATH.write_text(new_content, encoding="utf-8")
    print("[SUCCESS] Successfully mounted faas_carnage_telemetry router into faas_server.py.")
    return 0


if __name__ == "__main__":
    sys.exit(patch_faas_server())
