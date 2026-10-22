#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p .state

LOCK_FILE="/home/james/stacklabs/vfs/.state/DISCORD_MUTE.lock"
PENDING_FILE=".state/pending_query.json"

# 1. Master Mute Gate
if [[ -f "$LOCK_FILE" ]]; then
    exit 0
fi

# 2. Check for pending query
if [[ -f "$PENDING_FILE" ]]; then
    echo "DELTA_EXIT_1: Inbound savant query pending execution" >&2
    exit 1
fi

exit 0
