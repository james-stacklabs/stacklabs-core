#!/bin/bash
# ==============================================================================
# Sovereign OS - Lightweight State Synchronization to Google Drive
# Governed by STRY8791010 - Automated Ticket Ledger and Artifact Synchronization
# ==============================================================================

set -eu

# Concurrency lock protection
exec 200>/tmp/sovereign_sync_lightweight.lock
if ! flock -n 200; then
  echo "⚠️ Another instance of sync_lightweight.sh is already running. Exiting cleanly."
  exit 0
fi

TARGET_NOTEBOOK_DIR="/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal"
LIGHTWEIGHT_REMOTE="sovereign_os:SovereignOS_Clio_Sync/Lightweight"

echo "📡 INITIATING LIGHTWEIGHT STATE SYNC..."

# Check if lightweight sync is enabled in database
SYNC_ENABLED=$(/home/james/stacklabs/.venv/bin/python3 -c "import sqlite3; conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db'); cur = conn.cursor(); cur.execute(\"SELECT value FROM sys_properties WHERE name = 'system.lightweight_sync.enabled'\"); row = cur.fetchone(); conn.close(); print(row[0].strip().lower() == 'true' if row else 'true')")
if [ "$SYNC_ENABLED" != "True" ] && [ "$SYNC_ENABLED" != "true" ]; then
  echo "📡 Lightweight Sync is disabled via sys_properties. Exiting."
  exit 0
fi


# 1. Compile fresh database transfer packages (fast)
echo "Compiling live database transfer packages..."
python3 /home/james/stacklabs/scripts/compile_massive_notebook_payload.py
python3 /home/james/stacklabs/scripts/generate_persona_audit.py
echo "Compiling weekly epoch chronicles and staging epoch sources..."
python3 /home/james/stacklabs/scripts/compile_weekly_chronicles.py


# Ensure directories exist
mkdir -p "$TARGET_NOTEBOOK_DIR/walkthroughs"
mkdir -p "$TARGET_NOTEBOOK_DIR/implementation_plans"
mkdir -p "$TARGET_NOTEBOOK_DIR/docs"
mkdir -p "$TARGET_NOTEBOOK_DIR/work_orders"

# 2. Stage split database payloads, walkthroughs, plans, and docs
echo "Staging updated documents..."
rm -f "$TARGET_NOTEBOOK_DIR/SOVEREIGN_OS_INTERNAL_MASSIVE_DATA_TRANSFER_PACKAGE"*
rm -f "$TARGET_NOTEBOOK_DIR/SOVEREIGN_CODEBASE_PART_"*
rm -f "$TARGET_NOTEBOOK_DIR/"*.md.txt
rm -f "$TARGET_NOTEBOOK_DIR/work_orders/"*
for part_file in /home/james/stacklabs/dna/notebook_lm_exports/SOVEREIGN_OS_INTERNAL_MASSIVE_DATA_TRANSFER_PACKAGE_PART_*.txt; do
  if [ -f "$part_file" ]; then
    cp "$part_file" "$TARGET_NOTEBOOK_DIR/$(basename "$part_file")"
  fi
done

for part_file in /home/james/stacklabs/dna/notebook_lm_exports/SOVEREIGN_CODEBASE_PART_*.md; do
  if [ -f "$part_file" ]; then
    cp "$part_file" "$TARGET_NOTEBOOK_DIR/$(basename "$part_file")"
  fi
done

# Copy documentation files
find /home/james/stacklabs_inbox/walkthroughs/ -name "walkthrough_*.md" -type f 2>/dev/null | while read -r f; do
  cp "$f" "$TARGET_NOTEBOOK_DIR/walkthroughs/$(basename "$f")"
done

find /home/james/stacklabs_inbox/implementation_plans/ -name "implementation_plan_*.md" -type f 2>/dev/null | while read -r f; do
  cp "$f" "$TARGET_NOTEBOOK_DIR/implementation_plans/$(basename "$f")"
done

find /home/james/stacklabs/dna/docs/ -name "*.md" -type f 2>/dev/null | while read -r f; do
  cp "$f" "$TARGET_NOTEBOOK_DIR/docs/$(basename "$f")"
done

find /home/james/stacklabs_inbox/queue/archive/ /home/james/stacklabs_inbox/work_orders/ -name "*.md" -type f -mtime -7 2>/dev/null | while read -r f; do
  cp "$f" "$TARGET_NOTEBOOK_DIR/work_orders/$(basename "$f")"
done

# Ensure root bedrock laws and active session report are fresh
if [ -f "/home/james/stacklabs/dna/SOVEREIGN_DNA.md" ]; then
  cp "/home/james/stacklabs/dna/SOVEREIGN_DNA.md" "$TARGET_NOTEBOOK_DIR/SOVEREIGN_DNA.md"
fi

LATEST_SESSION_REPORT=$(find /home/james/stacklabs_inbox/today/ /home/james/stacklabs/dna/archives/sessions/ -name "SESSION_REPORT_*.md" -type f 2>/dev/null | sort -r | head -n 1)
if [ -n "$LATEST_SESSION_REPORT" ] && [ -f "$LATEST_SESSION_REPORT" ]; then
  cp "$LATEST_SESSION_REPORT" "$TARGET_NOTEBOOK_DIR/ACTIVE_SESSION_REPORT.md"
fi

# 2.1 Stage dedicated today/ daily additions folder for 1-click NotebookLM ingestion
mkdir -p "$TARGET_NOTEBOOK_DIR/today"
rm -f "$TARGET_NOTEBOOK_DIR/today/"*

# Copy today's session report(s)
find /home/james/stacklabs_inbox/today/ -name "SESSION_REPORT_*.md" -type f 2>/dev/null | while read -r f; do
  cp "$f" "$TARGET_NOTEBOOK_DIR/today/$(basename "$f")"
done

# Copy walkthroughs generated/modified in the past 24 hours (86400s)
find /home/james/stacklabs_inbox/walkthroughs/ -name "walkthrough_*.md" -type f -mtime -1 2>/dev/null | while read -r f; do
  cp "$f" "$TARGET_NOTEBOOK_DIR/today/$(basename "$f")"
done

# Copy new REQ/SOW specs created/modified in the past 24 hours
find /home/james/stacklabs/dna/docs/ -type f \( -name "REQ_*.md" -o -name "SOW_*.md" -o -name "*WHITEPAPER*.md" -o -name "*whitepaper*.md" \) -mtime -1 2>/dev/null | while read -r f; do
  cp "$f" "$TARGET_NOTEBOOK_DIR/today/$(basename "$f")"
done

# Generate daily ingestion manifest
TODAY_DATE=$(date +"%Y-%m-%d")
cat <<EOF > "$TARGET_NOTEBOOK_DIR/today/00_DAILY_INGESTION_MANIFEST_${TODAY_DATE}.txt"
================================================================================
STACKLABS LLC NOTEBOOKLM DAILY INGESTION MANIFEST
Date: ${TODAY_DATE}
Generated by: Sovereign Shutdown Protocol
Target Notebook: https://notebooklm.google.com/notebook/30ab3645-0681-45ed-9214-3f538c02c21c
================================================================================
The files in this 'today/' folder represent 100% of new verified engineering
deliverables produced during today's shift.

INSTRUCTIONS:
1. In NotebookLM, click '+ Add Sources' -> 'Google Drive'.
2. Navigate to: SovereignOS_Clio_Sync -> NotebookLM_Sync -> StackLabs_Internal -> today
3. Select All files in 'today/' and click Insert.
================================================================================
EOF

# 3. Mirror the NotebookLM directory to Google Drive with Strict Whitelist Filter
echo "Syncing NotebookLM target directory (StackLabs_Internal)..."
rclone sync "$TARGET_NOTEBOOK_DIR" "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/StackLabs_Internal" \
  --fast-list \
  --filter-from "/home/james/stacklabs/dna/sync/notebooklm_sync_filter.txt" \
  --delete-excluded \
  --quiet

# 3.05 Mirror Epoch Sources directly to Google Drive
echo "Syncing Epoch Sources partition to Google Drive..."
rclone sync "$TARGET_NOTEBOOK_DIR/epoch_sources" "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/StackLabs_Internal/epoch_sources" \
  --fast-list \
  --progress \
  --quiet


# 3.1 Mirror decoupled raw transcripts to separate archive partition
RAW_TRANSCRIPTS_DIR="/home/james/stacklabs_inbox/notebook_sync/Sovereign_Raw_Transcripts"
if [ -d "$RAW_TRANSCRIPTS_DIR" ]; then
  echo "Syncing raw transcripts archive partition..."
  rclone sync "$RAW_TRANSCRIPTS_DIR" "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/Sovereign_Raw_Transcripts" \
    --fast-list \
    --quiet
fi

# 4. Copy raw database file and other critical system directories
echo "Backing up raw DB and system directories..."
rclone copy "/home/james/stacklabs/dna/sovereign_now.db" "$LIGHTWEIGHT_REMOTE/dna/" --quiet
rclone copy "/home/james/stacklabs/dna/docs/" "$LIGHTWEIGHT_REMOTE/dna/docs/" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet
rclone copy "/home/james/stacklabs/logs/" "$LIGHTWEIGHT_REMOTE/logs/" --quiet
rclone copy "/home/james/stacklabs_inbox/walkthroughs/" "$LIGHTWEIGHT_REMOTE/inbox/walkthroughs/" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet
rclone copy "/home/james/stacklabs_inbox/implementation_plans/" "$LIGHTWEIGHT_REMOTE/inbox/implementation_plans/" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet
rclone copy "/home/james/stacklabs_inbox/reports/" "$LIGHTWEIGHT_REMOTE/inbox/reports/" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet

# 5. Run artifact harvester
echo "Harvesting artifacts..."
python3 /home/james/stacklabs/scripts/artifact_harvester.py

# 6. Bidirectional Sync of Harvested Assets, Walkthroughs, and Plans
echo "Syncing harvested artifacts (bidirectional copy)..."
rclone copy "sovereign_os:SovereignOS_Clio_Sync/Harvested_Artifacts" "/home/james/stacklabs/media_vault/03_Assets/Harvested_Artifacts" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet
rclone copy "/home/james/stacklabs/media_vault/03_Assets/Harvested_Artifacts" "sovereign_os:SovereignOS_Clio_Sync/Harvested_Artifacts" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet

echo "Syncing lookbooks (bidirectional copy)..."
rclone copy "sovereign_os:SovereignOS_Clio_Sync/SovereignOS/media_vault/03_Assets/Lookbooks" "/home/james/stacklabs/media_vault/03_Assets/Lookbooks" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet
rclone copy "/home/james/stacklabs/media_vault/03_Assets/Lookbooks" "sovereign_os:SovereignOS_Clio_Sync/SovereignOS/media_vault/03_Assets/Lookbooks" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet

echo "Syncing walkthroughs and plans (bidirectional copy)..."
rclone copy "sovereign_os:SovereignOS_Clio_Sync/walkthroughs" "/home/james/stacklabs_inbox/walkthroughs" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet
rclone copy "/home/james/stacklabs_inbox/walkthroughs" "sovereign_os:SovereignOS_Clio_Sync/walkthroughs" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet

rclone copy "sovereign_os:SovereignOS_Clio_Sync/implementation_plans" "/home/james/stacklabs_inbox/implementation_plans" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet
rclone copy "/home/james/stacklabs_inbox/implementation_plans" "sovereign_os:SovereignOS_Clio_Sync/implementation_plans" --exclude "node_modules/**" --exclude "dist/**" --exclude ".git/**" --quiet

echo "🟢 Lightweight state sync completed successfully."
