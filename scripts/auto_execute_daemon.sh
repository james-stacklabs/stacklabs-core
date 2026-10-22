#!/bin/bash
# ==============================================================================
# Sovereign OS: Automated Ticket Execution Daemon Loop
# Path: /home/james/stacklabs/scripts/auto_execute_daemon.sh
# ==============================================================================

echo "Starting Sovereign ticket execution daemon loop..."

while true; do
    /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/auto_execute_preapproved.py
    sleep 60
done
