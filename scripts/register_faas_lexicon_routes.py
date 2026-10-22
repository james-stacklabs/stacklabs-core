#!/home/james/stacklabs/.venv/bin/python3
"""
Idempotent registration of /api/faas/lexicon/bursts and /api/faas/lexicon/drilldown in scripts/faas_server.py.
Path: /home/james/stacklabs/scripts/register_faas_lexicon_routes.py
"""
import os
import sys
import tempfile
from pathlib import Path

FAAS_SERVER_PATH = Path("/home/james/stacklabs/scripts/faas_server.py")


def register_routes() -> None:
    if not FAAS_SERVER_PATH.exists():
        print(f"ERROR: {FAAS_SERVER_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    content = FAAS_SERVER_PATH.read_text(encoding="utf-8")
    if "faas_lexicon_router" in content:
        print("OK: faas_lexicon_router already mounted in scripts/faas_server.py.")
        return

    mount_block = """
# Mount /api/faas/lexicon/bursts and /api/faas/lexicon/drilldown (WO0011212)
try:
    from scripts.blueprints.faas_vfs_telemetry import faas_lexicon_router
    app.include_router(faas_lexicon_router)
except Exception as _lex_exc:
    print(f"[FaaS Server] Lexicon router mount warning: {_lex_exc}")
"""
    if "app.include_router(" in content:
        idx = content.find("app.include_router(")
        line_end = content.find("\n", idx)
        new_content = content[: line_end + 1] + mount_block + content[line_end + 1 :]
    else:
        new_content = content.rstrip() + "\n" + mount_block + "\n"

    with tempfile.NamedTemporaryFile("w", dir=str(FAAS_SERVER_PATH.parent), delete=False, encoding="utf-8") as tf:
        tf.write(new_content)
        tmp_name = tf.name
    os.replace(tmp_name, str(FAAS_SERVER_PATH))
    print("SUCCESS: Mounted faas_lexicon_router (/api/faas/lexicon/bursts) in scripts/faas_server.py.")


if __name__ == "__main__":
    register_routes()
