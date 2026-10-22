#!/home/james/stacklabs/.venv/bin/python3
"""
Wires a 12-line direct VFS file reader into scripts/faas_server.py (WO0011282).
Zero separate blueprints, zero SQLite queries on the request path.
"""
from __future__ import annotations

import os
from pathlib import Path

SERVER_FILE = Path("/home/james/stacklabs/scripts/faas_server.py")

ROUTE_SNIPPET = '''
@app.get("/api/snipe/{snipe_id}/time_machine")
def serve_vfs_snipe_time_machine(snipe_id: str):
    from scripts.vfs_snipe_time_machine import VFS_SNIPES, DATA_SNIPES, build_snipe_time_machine
    import json
    for base in (VFS_SNIPES, DATA_SNIPES):
        p = base / snipe_id / "time_machine.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return build_snipe_time_machine(snipe_id)
'''


def main() -> None:
    text = SERVER_FILE.read_text(encoding="utf-8")
    if "serve_vfs_snipe_time_machine" in text:
        print("Route already present in faas_server.py.")
        return
    anchor = "# Mount FaaS Time Machine Blueprint"
    if anchor in text:
        patched = text.replace(anchor, ROUTE_SNIPPET.lstrip() + "\n" + anchor, 1)
    elif "# STATIC FILES SERVING & SPA FALLBACK" in text:
        patched = text.replace(
            "# STATIC FILES SERVING & SPA FALLBACK",
            ROUTE_SNIPPET.lstrip() + "\n# STATIC FILES SERVING & SPA FALLBACK",
            1,
        )
    else:
        patched = text.rstrip() + "\n\n" + ROUTE_SNIPPET.lstrip()
    tmp = SERVER_FILE.with_suffix(".py.tmp")
    tmp.write_text(patched, encoding="utf-8")
    os.replace(tmp, SERVER_FILE)
    print("Appended direct VFS time_machine file route to faas_server.py.")


if __name__ == "__main__":
    main()
