#!/bin/bash
# ==============================================================================
# Sovereign OS // Docs Sync Watcher
# Function: Automatically watches dna/docs/ and syncs all markdown files
#           to Google Drive workspace backup and NotebookLM staging directory
#           immediately on file save, move, or delete.
# ==============================================================================

WATCH_DIR="/home/james/stacklabs/dna/docs"
GDRIVE_TARGET_WORKSPACE="sovereign_os:SovereignOS_Clio_Sync/SovereignOS/dna/docs"
GDRIVE_TARGET_NOTEBOOK="sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/StackLabs_Internal/docs"
STAGE_DIR="/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/docs"
LOG="/home/james/stacklabs/scripts/docs_sync.log"

# Ensure staging directory exists
mkdir -p "$STAGE_DIR"

echo "[DOCS SYNC] Watcher daemon armed. Monitoring $WATCH_DIR..." | tee -a "$LOG"

check_docs_sync_enabled() {
  /home/james/stacklabs/.venv/bin/python3 -c "import sqlite3; conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db'); cur = conn.cursor(); cur.execute(\"SELECT value FROM sys_properties WHERE name = 'system.docs_sync.enabled'\"); row = cur.fetchone(); conn.close(); print(row[0].strip().lower() == 'true' if row else 'true')"
}

# Helper to stage a file with a timestamp
stage_with_timestamp() {
  local src="$1"
  local dest="$2"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%d %H:%M:%S")
  echo "**LAST SYNC TIME:** ${timestamp} UTC" > "$dest"
  echo "" >> "$dest"
  cat "$src" >> "$dest"
}

# Run a sync immediately on startup if enabled
echo "[DOCS SYNC] Performing initial check..." | tee -a "$LOG"
if [ "$(check_docs_sync_enabled)" = "True" ] || [ "$(check_docs_sync_enabled)" = "true" ]; then
  echo "[DOCS SYNC] Performing initial synchronization sweep..." | tee -a "$LOG"
  # 1. Sync raw workspace docs folder
  rclone sync "$WATCH_DIR" "$GDRIVE_TARGET_WORKSPACE" -v 2>> "$LOG"

  # 2. Stage to NotebookLM folder and sync
  rm -f "$STAGE_DIR"/*
  find "$WATCH_DIR" -name "*.md" -type f 2>/dev/null | while read -r f; do
    if [ -f "$f" ]; then
      stage_with_timestamp "$f" "$STAGE_DIR/$(basename "$f")"
    fi
  done
  rclone sync "$STAGE_DIR" "$GDRIVE_TARGET_NOTEBOOK" -v 2>> "$LOG"
  echo "[DOCS SYNC] Initial sweep completed." | tee -a "$LOG"
else
  echo "[DOCS SYNC] Docs sync is disabled via sys_properties. Skipping initial sweep." | tee -a "$LOG"
fi

# Monitor the directory for close_write, moved_to, and delete events
inotifywait -m -r -e close_write,moved_to,delete "$WATCH_DIR" |
while read -r directory events filename; do
    # Only react to markdown files to avoid sync loops on temporary files
    if [[ "$filename" =~ \.md$ ]]; then
        echo "[DOCS SYNC] $(date) — Change detected in $directory: $filename ($events)" | tee -a "$LOG"
        
        if [ "$(check_docs_sync_enabled)" = "True" ] || [ "$(check_docs_sync_enabled)" = "true" ]; then
            # 1. Sync workspace backup folder on Google Drive
            rclone sync "$WATCH_DIR" "$GDRIVE_TARGET_WORKSPACE" -v 2>> "$LOG"
            
            # 2. Re-stage all docs and sync NotebookLM target folder
            rm -f "$STAGE_DIR"/*
            find "$WATCH_DIR" -name "*.md" -type f 2>/dev/null | while read -r f; do
                if [ -f "$f" ]; then
                    stage_with_timestamp "$f" "$STAGE_DIR/$(basename "$f")"
                fi
            done
            rclone sync "$STAGE_DIR" "$GDRIVE_TARGET_NOTEBOOK" -v 2>> "$LOG"
            
            echo "[DOCS SYNC] $(date) — Push completed." | tee -a "$LOG"
        else
            echo "[DOCS SYNC] $(date) — Docs sync is disabled via sys_properties. Skipping synchronization." | tee -a "$LOG"
        fi
    fi
done

