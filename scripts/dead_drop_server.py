#!/usr/bin/env python3
"""
StackLabs Sovereign Drop Gateway (Modular V2 Decoupled Production Entry)
Target Size: <= 400 lines (Invariant 50 Compliance)
"""
import sys
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scripts.dead_drop_server_v2 import app, logger
from scripts.blueprints.sync_bp import discover_notebook_envelopes, get_smart_icon  # noqa: F401

if __name__ == '__main__':
    logger.info("⚡ Starting StackLabs Ingress Gateway on production port 8088...")
    app.run(host='127.0.0.1', port=8088, debug=False, threaded=True)
