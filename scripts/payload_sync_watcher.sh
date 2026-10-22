#!/bin/bash

# ==============================================================================
# MASTER PAYLOAD SYNC DAEMON
# Function: Mirrors all localized Agent "payloads" directories to Google Drive.
#           Bypasses the broken DOM scraper and enables Native NotebookLM 
#           and @Google Drive ingest for cloud-hosted AI Gems.
# ==============================================================================

AGENTS_DIR="/home/james/stacklabs/dna/agents"
GDRIVE_ROOT="sovereign_os:Sovereign_OS_Master_Payloads"
LOG="/home/james/stacklabs/scripts/payload_sync.log"

echo "[PAYLOAD SYNC] Master daemon armed. Polling all Agent directories every 60 seconds..." | tee -a "$LOG"

while true; do
    echo "[PAYLOAD SYNC] $(date) — Initiating Fleet Sweep..." >> "$LOG"
    
    # Dynamically sweep through all existing agent directories
    for agent_dir in "$AGENTS_DIR"/*/; do
        # Check if the payloads folder explicitly exists to avoid syncing empty trash
        if [ -d "${agent_dir}payloads" ]; then
            agent_name=$(basename "$agent_dir")
            
            # Sync the contents of the local payloads directory to the specific Agent's GDrive folder
            rclone sync "${agent_dir}payloads" "$GDRIVE_ROOT/$agent_name" -v 2>> "$LOG"
        fi
    done
    
    # SOVEREIGN DROPZONE SYNC: Mirror the entire dropzone seamlessly
    echo "[PAYLOAD SYNC] $(date) — Commencing Dropzone Sync to Cloud..." >> "$LOG"
    rclone sync "/home/james/stacklabs/dna/dropzone/" "$GDRIVE_ROOT/Dropzone/" -v 2>> "$LOG"

    # ORBIT 3 CLOUD ARCHIVE: Push the MP4s from Ghost Drive up to the 30TB void
    echo "[PAYLOAD SYNC] $(date) — Commencing Orbit 3 Archive to Cloud..." >> "$LOG"
    rclone copy /mnt/ghost_drive/hailo_dropzone/ "$GDRIVE_ROOT/MEDIA_ARCHIVE/" --bwlimit 5M -v 2>> "$LOG"
    
    # PEGASUS .177 MOUNT: Push incoming M.A.R.D. artifacts to cloud
    echo "[PAYLOAD SYNC] $(date) — Monitoring .177 mount for M.A.R.D. artifacts..." >> "$LOG"
    if [ -d "/mnt/node_177" ]; then
        rclone copy "/mnt/node_177" "$GDRIVE_ROOT/Pegasus_MARD_Artifacts/" -v 2>> "$LOG"
    fi
    
    # Run the SQLite Media Cataloger (WO-2026-115)
    echo "[PAYLOAD SYNC] $(date) — Commencing SQLite Media Cataloging..." >> "$LOG"
    python3 /home/james/stacklabs/scripts/catalog_media.py >> "$LOG" 2>&1
    
    echo "[PAYLOAD SYNC] $(date) — Sweep complete. Sleeping 60s." >> "$LOG"
    sleep 60
done
