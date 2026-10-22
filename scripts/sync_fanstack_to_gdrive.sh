#!/bin/bash
# FanStack - GDrive Synchronization Pipeline
# Governed by RULE 11 (Session State Synchronization) - Decoupled FanStack Layer

echo "📡 INITIATING FANSTACK CLOUD BACKUP..."

# Ensure rclone is installed
if ! command -v rclone &> /dev/null; then
    echo "⚠️ ALERT: rclone is not installed. Sync bypassed."
    exit 1
fi

# 1. Sync Game Room Chat Exports
echo "✅ Syncing Game Room chat exports..."
rclone sync /home/james/stacklabs/data/logs sovereign_os:SovereignOS_Clio_Sync/SovereignOS/data/logs --progress

# 2. Sync FanStack Daemon Logs
echo "✅ Syncing FanStack daemon logs..."
rclone sync /home/james/stacklabs/logs sovereign_os:SovereignOS_Clio_Sync/SovereignOS/logs --progress

# 3. Sync Game Cache States
echo "✅ Syncing live game states cache..."
rclone sync /home/james/stacklabs/game_states sovereign_os:SovereignOS_Clio_Sync/SovereignOS/game_states --progress

# 4. Sync Frontend Codebase (excluding node_modules/dist)
echo "✅ Syncing FanStack frontend source code..."
rclone sync /home/james/stacklabs/15_FanStack sovereign_os:SovereignOS_Clio_Sync/SovereignOS/15_FanStack \
  --exclude "node_modules/**" \
  --exclude "dist/**" \
  --progress

echo "✅ FanStack Sync Complete. Shared memory is secure."
