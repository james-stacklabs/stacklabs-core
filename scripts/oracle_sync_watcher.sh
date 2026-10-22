#!/bin/bash
WATCH_DIR="/home/james/stacklabs/dna/agents/SOVEREIGN_ORACLE/payloads"
GDRIVE_TARGET="sovereign_os:SOVEREIGN_ORACLE_Payloads"
LOG="/home/james/stacklabs/scripts/oracle_sync.log"

echo "[ORACLE SYNC] Watcher armed. Watching $WATCH_DIR..." | tee -a $LOG

inotifywait -m -e close_write,moved_to "$WATCH_DIR" |
while read -r directory events filename; do
    echo "[ORACLE SYNC] $(date) — New file detected: $filename" | tee -a $LOG
    rclone copyto "$WATCH_DIR/$filename" "$GDRIVE_TARGET/$filename" -v 2>> $LOG
    echo "[ORACLE SYNC] $(date) — $filename pushed to Drive." | tee -a $LOG
done
