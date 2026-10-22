#!/usr/bin/env bash
# 🧠 Sovereign OS NotebookLM Sync Automation (.txt extension format)
# Path: /home/james/stacklabs/scripts/sync_notebook.sh
# Deprecated/Paused: Delegating exclusively to sync_to_gdrive.sh (StackLabs - Internal)

set -euo pipefail

echo "======================================================================"
echo "⚠️  SovereignOS public/external notebook sync is PAUSED per Pilot request."
echo "➡️  Delegating sync to StackLabs - Internal (sync_to_gdrive.sh)..."
echo "======================================================================"
echo

exec "/home/james/stacklabs/scripts/sync_to_gdrive.sh" "$@"

