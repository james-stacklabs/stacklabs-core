#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p .state deps
# Master Stigmergic Mute Check
if [[ -f "/home/james/stacklabs/vfs/.state/DISCORD_MUTE.lock" ]]; then
    exit 0
fi

DB_FILE="deps/wiretap.db"
if [[ ! -e "$DB_FILE" ]]; then
    ln -sfn /home/james/stacklabs/data/morning_wiretap.db deps/wiretap.db
fi

WINDOW_SEC=$(jq -r '.bindings.window_seconds // 15' spec.json 2>/dev/null || echo 15)
MIN_MSGS=$(jq -r '.bindings.velocity_threshold_msgs // 10' spec.json 2>/dev/null || echo 10)
COOLDOWN_SEC=$(jq -r '.bindings.cooldown_per_team_sec // 120' spec.json 2>/dev/null || echo 120)

# 1. If an unhandled pending burst is already staged, trigger reflex immediately
if [[ -f .state/pending_burst.json ]]; then
    echo "DELTA_EXIT_1: Pending velocity burst staged for execution" >&2
    exit 1
fi

# 2. Query recent chat velocity grouped by channel_key in read-only mode
BURST_ROWS=$(sqlite3 -json "file:deps/wiretap.db?mode=ro" "
  SELECT 
    channel_key, 
    stream_id, 
    COUNT(*) as msg_count, 
    MIN(epoch_time) as window_start, 
    MAX(epoch_time) as window_end
  FROM chat_telemetry 
  WHERE epoch_time > (strftime('%s', 'now') - ${WINDOW_SEC})
  GROUP BY channel_key 
  HAVING msg_count >= ${MIN_MSGS}
  ORDER BY msg_count DESC;
" 2>/dev/null || echo "[]")

ROW_COUNT=$(echo "$BURST_ROWS" | jq 'length')
if (( ROW_COUNT == 0 )); then
    exit 0
fi

COOLDOWNS_FILE=".state/team_cooldowns.json"
NOW=$(date +%s)

# Active primetime game filter: At night on Sunday, focus on active primetime slate (DAL, GB)
ACTIVE_PRIMETIME="DAL GB"

for (( idx=0; idx<ROW_COUNT; idx++ )); do
    ROW=$(echo "$BURST_ROWS" | jq -c ".[$idx]")
    CHANNEL=$(echo "$ROW" | jq -r '.channel_key // empty')
    if [[ -z "$CHANNEL" ]]; then
        continue
    fi

    # Extract canonical team abbreviation
    TEAM="NFL"
    if [[ "$CHANNEL" =~ ^([A-Z]{2,3})_ ]]; then
        TEAM="${BASH_REMATCH[1]}"
    elif [[ "$CHANNEL" =~ ([A-Z]{2,3})@([A-Z]{2,3}) ]]; then
        TEAM="${BASH_REMATCH[2]}"
    elif [[ "$CHANNEL" =~ ^([A-Z]{2,3}) ]]; then
        TEAM="${BASH_REMATCH[1]}"
    fi

    # If night window (after 8 PM EDT = 20:00), suppress dead afternoon game channels
    CURRENT_HOUR=$(date +%H)
    if (( CURRENT_HOUR >= 20 || CURRENT_HOUR < 4 )); then
        if [[ ! "$ACTIVE_PRIMETIME" =~ "$TEAM" ]]; then
            continue
        fi
    fi

    # Check team cooldown to prevent rapid spamming
    if [[ -f "$COOLDOWNS_FILE" ]]; then
        LAST_TEAM_TIME=$(jq -r --arg t "$TEAM" '.[$t] // 0' "$COOLDOWNS_FILE" 2>/dev/null || echo 0)
        AGE=$(( NOW - LAST_TEAM_TIME ))
        if (( AGE < COOLDOWN_SEC )); then
            continue
        fi
    fi

    # Stage burst for execution
    echo "$ROW" | jq --arg team "$TEAM" '. + {team: $team}' > .state/pending_burst.json
    echo "DELTA_EXIT_1: Live velocity burst detected on ${TEAM} (${CHANNEL}) with $(echo "$ROW" | jq -r '.msg_count') msgs in ${WINDOW_SEC}s" >&2
    exit 1
done

exit 0
