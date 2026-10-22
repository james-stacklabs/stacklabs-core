#!/bin/bash
cd /home/james/stacklabs
source .venv/bin/activate
exec python scripts/fanstack_mcp_server.py
