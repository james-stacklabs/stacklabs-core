#!/usr/bin/env bash
# 🧠 StackLabs Dual-NotebookLM Sync Automation
# Path: /home/james/stacklabs/scripts/sync_notebook_stacklabs.sh
# Deprecated/Paused: Delegating exclusively to sync_to_gdrive.sh (StackLabs - Internal)

set -euo pipefail

echo "======================================================================"
echo "⚠️  StackLabs Syndicate/External notebook sync is PAUSED per Pilot request."
echo "➡️  Delegating sync to StackLabs - Internal (sync_to_gdrive.sh)..."
echo "======================================================================"
echo

exec "/home/james/stacklabs/scripts/sync_to_gdrive.sh" "$@"

