#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p .state deps
# Master Stigmergic Mute Check
if [[ -f "/home/james/stacklabs/vfs/.state/DISCORD_MUTE.lock" ]]; then
    exit 0
fi

DB_FILE="deps/wiretap.db"
[[ ! -e "$DB_FILE" ]] && ln -sfn /home/james/stacklabs/data/morning_wiretap.db deps/wiretap.db
BARF_DIR="deps/barf"
[[ ! -e "$BARF_DIR" ]] && ln -sfn /home/james/stacklabs/vfs/advocates/barf_discord deps/barf

LAST_FILE=".state/last_defense.json"
BARF_BARK="deps/barf/.state/last_bark.json"
COOLDOWN=$(jq -r '.bindings.defense_cooldown_sec // 120' spec.json)

if [[ -f "$LAST_FILE" ]]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$LAST_FILE") ))
    if (( AGE < COOLDOWN )); then
        exit 0
    fi
fi

# Check if Barf mocked Dallas or if a new DAL burst occurred
if [[ -f "$BARF_BARK" ]]; then
    BARF_ID=$(jq -r '.alert_rowid // .burst_id // 0' "$BARF_BARK")
    BARF_GAME=$(jq -r '.game_id // ""' "$BARF_BARK")
    LAST_DEFENDED=$(jq -r '.defended_burst_id // .defense_burst_id // 0' "$LAST_FILE" 2>/dev/null || echo 0)
    
    if [[ "$BARF_GAME" == "DAL" && "$BARF_ID" != "$LAST_DEFENDED" ]]; then
        jq '.burst_id = (.alert_rowid // .burst_id)' "$BARF_BARK" > .state/pending_defense.json
        echo "DELTA_EXIT_1: Barf mocked Dallas (#${BARF_ID}); Larry must defend America's Team" >&2
        exit 1
    fi
fi

# Check wiretap for direct DAL burst
LAST_ID=$(jq -r '.defended_burst_id // .defense_burst_id // 0' "$LAST_FILE" 2>/dev/null || echo 0)
if ! [[ "$LAST_ID" =~ ^[0-9]+$ ]]; then
    LAST_ID=0
fi
ROW=$(sqlite3 -json "file:deps/wiretap.db?mode=ro" \
  "SELECT rowid AS burst_id, team_abbrev AS game_id, channel_key AS channel_name, z_score, peak_quote AS sample_text 
   FROM discord_burst_alerts 
   WHERE team_abbrev = 'DAL' AND rowid > ${LAST_ID} 
   ORDER BY rowid DESC LIMIT 1;" 2>/dev/null || echo "[]")

NEW_ID=$(echo "$ROW" | jq -r '.[0].burst_id // empty')
if [[ -n "$NEW_ID" ]]; then
    echo "$ROW" | jq '.[0]' > .state/pending_defense.json
    echo "DELTA_EXIT_1: Direct DAL burst #${NEW_ID} detected" >&2
    exit 1
fi

exit 0
