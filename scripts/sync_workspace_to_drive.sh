#!/bin/bash
# ==============================================================================
# Sovereign OS // Project Spark Workspace Sync Engine
# Governed by STRY-06052026-SPARK-WORKSPACE-SYNC
# ==============================================================================

SOURCE_DIR="/home/james/stacklabs"
TARGET_REMOTE="sovereign_os:SovereignOS_Clio_Sync/SovereignOS"

echo "📡 INITIATING STANDALONE WORKSPACE EXPORT PASS..."

# Enforce dependency validation checks
if ! command -v rclone &> /dev/null; then
    echo "❌ CRITICAL ERROR: rclone engine is missing from paths. Ingress aborted."
    exit 1
fi

echo "📦 Compiling raw source file layouts (excluding distribution artifacts)..."

rclone sync "$SOURCE_DIR" "$TARGET_REMOTE" \
    --exclude-from "/home/james/stacklabs/.rclone-ignore" \
    --checkers 16 \
    --transfers 8 \
    --fast-list \
    --progress \
    --max-age 24h

echo "🟢 SUCCESS: Workspace structure cleanly mirrored to Cloud Drive."
echo "➡️ Staged and ready for manual selection via Spark Folder Uploader."
