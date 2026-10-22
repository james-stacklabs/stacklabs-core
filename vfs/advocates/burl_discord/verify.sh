#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p .state
# Master Stigmergic Mute Check
if [[ -f "/home/james/stacklabs/vfs/.state/DISCORD_MUTE.lock" ]]; then
    exit 0
fi

BARF_BARK="deps/barf/.state/last_bark.json"
BURL_STATE=".state/last_drawl.json"
DELAY=$(jq -r '.bindings.porch_delay_sec' spec.json)

[[ ! -f "$BARF_BARK" ]] && exit 0

# 1. Porch Pace: Wait at least 45 seconds after Barf barks before drawling back
BARK_AGE=$(( $(date +%s) - $(stat -c %Y "$BARF_BARK") ))
if (( BARK_AGE < DELAY )); then
    exit 0
fi

BARF_ID=$(jq -r '.burst_id // 0' "$BARF_BARK")
BURL_ID=$(jq -r '.replied_to_burst_id // 0' "$BURL_STATE" 2>/dev/null || echo 0)

# 2. Check if Burl has already countered this Barf rant
if [[ "$BARF_ID" != "$BURL_ID" ]]; then
    cp "$BARF_BARK" .state/pending_counter.json
    echo "DELTA_EXIT_1: Barf barked (#${BARF_ID}) ${BARK_AGE}s ago; Burl hasn't countered yet" >&2
    exit 1
fi

exit 0
