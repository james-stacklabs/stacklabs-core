#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p .state
# Master Stigmergic Mute Check
if [[ -f "/home/james/stacklabs/vfs/.state/DISCORD_MUTE.lock" ]]; then
    exit 0
fi

BURL_DRAWL="deps/burl/.state/last_drawl.json"
BARF_BARK="deps/barf/.state/last_bark.json"
SAMMY_STATE=".state/last_ticket.json"
DELAY=$(jq -r '.bindings.diner_delay_sec' spec.json)

# Wait until both Barf and Burl have spoken on the play
[[ ! -f "$BURL_DRAWL" ]] || [[ ! -f "$BARF_BARK" ]] && exit 0

# 1. Diner Pace: Wait 30 seconds after Burl's drawl
DRAWL_AGE=$(( $(date +%s) - $(stat -c %Y "$BURL_DRAWL") ))
if (( DRAWL_AGE < DELAY )); then
    exit 0
fi

BURST_ID=$(jq -r '.replied_to_burst_id // 0' "$BURL_DRAWL")
GRADED_ID=$(jq -r '.graded_burst_id // 0' "$SAMMY_STATE" 2>/dev/null || echo 0)

# 2. Check if Sammy has already audited the Total & Calendar Parity
if [[ "$BURST_ID" != "$GRADED_ID" ]]; then
    jq -s '.[0] * .[1]' "$BARF_BARK" "$BURL_DRAWL" > .state/pending_audit.json
    echo "DELTA_EXIT_1: Burst #${BURST_ID} discussed by Barf & Burl; Sammy needs to audit the Total" >&2
    exit 1
fi

exit 0
