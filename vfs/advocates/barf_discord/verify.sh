#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p .state deps

# Master Stigmergic Mute Check
if [[ -f "/home/james/stacklabs/vfs/.state/DISCORD_MUTE.lock" ]]; then
    exit 0
fi

LAST_FILE=".state/last_bark.json"
COOLDOWN=$(jq -r '.bindings.cooldown_sec // 120' spec.json 2>/dev/null || echo 120)

# 1. Etiquette Gate: Check cooldown threshold
if [[ -f "$LAST_FILE" ]]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$LAST_FILE") ))
    if (( AGE < COOLDOWN )); then
        exit 0
    fi
fi

# 2. Extract strictly integer alert_rowid to prevent syntax errors
LAST_ROWID=$(jq -r '.alert_rowid // 0' "$LAST_FILE" 2>/dev/null || echo 0)
if ! [[ "$LAST_ROWID" =~ ^[0-9]+$ ]]; then
    LAST_ROWID=0
fi

# 3. Check symlinked morning_wiretap.db for newer burst alert
DB_FILE="/home/james/stacklabs/data/morning_wiretap.db"
ROW=$(sqlite3 -json "file:${DB_FILE}?mode=ro" \
  "SELECT rowid AS alert_rowid, alert_id AS burst_id, team_abbrev AS game_id, channel_key AS channel_name, z_score, peak_author, peak_quote AS sample_text 
   FROM discord_burst_alerts 
   WHERE rowid > ${LAST_ROWID} ORDER BY rowid DESC LIMIT 1;" 2>/dev/null || echo "[]")

NEW_ROWID=$(echo "$ROW" | jq -r '.[0].alert_rowid // empty')

if [[ -n "$NEW_ROWID" ]]; then
    echo "$ROW" | jq '.[0]' > .state/pending_burst.json
    echo "DELTA_EXIT_1: Unbarked burst #${NEW_ROWID}" >&2
    exit 1
fi

exit 0
