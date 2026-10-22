#!/bin/bash
# Sovereign Agent Sync Protocol: ROMEO
# Synchronizes the local Romeo DNA folder to Google Drive via rclone

LOCAL_DIR="/home/james/stacklabs/dna/agents/ROMEO/"
REMOTE_DIR="sovereign_os:Sovereign_Agents/ROMEO_BACKUPS"

echo "===================================================="
echo "🚀 INITIATING SOVEREIGN SYNC: ROMEO -> GOOGLE DRIVE"
echo "===================================================="
echo "Local Path: $LOCAL_DIR"
echo "Remote Path: $REMOTE_DIR"
echo "Starting rclone sync..."

# Execute rclone sync (this will overwrite the remote with exactly what is local)
rclone sync "$LOCAL_DIR" "$REMOTE_DIR" --progress --verbose

echo ""
echo "✅ SYNC COMPLETE."
echo "All Romeo artifacts, payloads, and chat logs are safely backed up to Google Drive."
echo ""
echo "To automate this every hour, add the following to your crontab (crontab -e):"
echo "0 * * * * /home/james/stacklabs/scripts/sync_romeo_to_gdrive.sh >> /tmp/romeo_sync.log 2>&1"
echo "===================================================="
