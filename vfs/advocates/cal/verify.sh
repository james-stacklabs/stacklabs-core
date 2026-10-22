#!/usr/bin/env bash
set -euo pipefail

cd /home/james/stacklabs

if [[ -f "vfs/.state/DISCORD_MUTE.lock" ]]; then
    exit 0
fi

STATE_FILE="vfs/advocates/cal/.state/last_audit.json"
DB_PATH="data/morning_wiretap.db"

if [[ ! -f "$DB_PATH" ]]; then
    exit 0
fi

LAST_ID=0
if [[ -f "$STATE_FILE" ]]; then
    EXTRACTED=$(jq -r '.alert_rowid // 0' "$STATE_FILE" 2>/dev/null || echo "0")
    if [[ "$EXTRACTED" =~ ^[0-9]+$ ]]; then
        LAST_ID="$EXTRACTED"
    fi
fi

TableExists=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cal_tape_alerts';" 2>/dev/null || echo "0")
if [[ "$TableExists" != "1" ]]; then
    exit 0
fi

PENDING=$(sqlite3 "$DB_PATH" "SELECT COALESCE(MAX(id), 0) FROM cal_tape_alerts WHERE id > ${LAST_ID} AND dispatched = 0;" 2>/dev/null || echo "0")
if [[ "$PENDING" =~ ^[0-9]+$ ]] && (( PENDING > LAST_ID )); then
    exit 1
fi

exit 0
