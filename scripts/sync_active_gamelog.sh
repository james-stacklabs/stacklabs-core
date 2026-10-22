#!/bin/bash
# ==============================================================================
# Sovereign OS - Live Game Log Synchronization Loop
# STRY-06072026-LOG-INTEGRATION — Phase 3: The 5-Minute Sync Loop
# ==============================================================================

GAME_PK="823206"
OUTPUT_DIR="/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal"
OUTPUT_FILE="$OUTPUT_DIR/game_log_${GAME_PK}_live.md"
PILOT_FILE="/home/james/stacklabs/pilot_drops/game_log_${GAME_PK}_20260626.md"

mkdir -p "$OUTPUT_DIR"
mkdir -p "/home/james/stacklabs/pilot_drops"

echo "=== Gamelog Sync Started: Game PK ${GAME_PK} ==="

while true; do
    echo "[$(date)] Syncing game log for ${GAME_PK}..."
    
    # Fetch log from local relay API
    curl -s "http://127.0.0.1:8000/api/game-log/export/${GAME_PK}?format=md" > "$OUTPUT_FILE"
    
    # Also sync to pilot drops path
    cp "$OUTPUT_FILE" "$PILOT_FILE"
    
    # Log progress
    echo "[$(date)] Sync completed. Staged in $OUTPUT_FILE and $PILOT_FILE."
    
    # Wait for 5 minutes
    sleep 300
done
