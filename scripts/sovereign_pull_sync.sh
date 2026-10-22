#!/usr/bin/env bash
# ==============================================================================
# Sovereign OS: Unified Google Drive Work Order Pull & Sync Script (Streamlined v2.0)
# Path: /home/james/stacklabs/scripts/sovereign_pull_sync.sh
#
# Governed by STRY8791010 / WO-20260830.
# Scoped, fast pull from Google Drive, automatic Markdown conversion,
# Decision Derby semantic classification, and safe atomic cloud archiving.
# ==============================================================================

set -euo pipefail

export DISPLAY=""
export PLAYWRIGHT_HEADLESS=true

# Design Token Colors for Clio Terminal Output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SOVEREIGN_HOME="/home/james/stacklabs"
VENV_PYTHON="${SOVEREIGN_HOME}/.venv/bin/python3"
[ ! -f "$VENV_PYTHON" ] && VENV_PYTHON="python3"

GDRIVE_SOURCE_SPARK="stacklabs_edge:work_orders"
GDRIVE_ARCHIVE="stacklabs_edge:work_orders/archive"
LOCAL_INBOX="/home/james/stacklabs_inbox"
QUEUE_INCOMING="${LOCAL_INBOX}/queue/incoming"
QUEUE_ARCHIVE="${LOCAL_INBOX}/queue/archive"
QUEUE_EXECUTED="${LOCAL_INBOX}/executed"
WO_STAGING="${LOCAL_INBOX}/.wo_staging"
DECISION_DERBY_SCRIPT="${SOVEREIGN_HOME}/scripts/organize_inbox.py"
DB_PATH="${SOVEREIGN_HOME}/dna/sovereign_now.db"
SYNC_LOG_FILE="${SOVEREIGN_HOME}/logs/sync.log"

mkdir -p "$(dirname "$SYNC_LOG_FILE")"
mkdir -p "$LOCAL_INBOX/walkthroughs" "$LOCAL_INBOX/implementation_plans" "$LOCAL_INBOX/reports" "$QUEUE_EXECUTED" "$QUEUE_ARCHIVE" "$LOCAL_INBOX/kb" "$QUEUE_INCOMING" "$WO_STAGING"

log_sync_event() {
    local status="$1"
    local msg="$2"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$status] $msg" >> "$SYNC_LOG_FILE"
    
    if [ -f "$SYNC_LOG_FILE" ] && [ "$(wc -l < "$SYNC_LOG_FILE")" -gt 500 ]; then
        tail -n 500 "$SYNC_LOG_FILE" > "$SYNC_LOG_FILE.tmp" && mv "$SYNC_LOG_FILE.tmp" "$SYNC_LOG_FILE"
    fi
}

log_sync_event "syncing" "Sovereign pull sync pass initiated."
echo -e "${CYAN}[*] Initiating Sovereign Google Drive Sync Pass...${NC}"

# 1. Sync Walkthroughs and Plans (Scoped & Fast)
echo -e "${CYAN}[➔] Syncing walkthroughs and plans from Google Drive...${NC}"
rclone copy "sovereign_os:SovereignOS_Clio_Sync/walkthroughs" "$LOCAL_INBOX/walkthroughs" --fast-list --max-depth 1 --quiet || true
rclone copy "sovereign_os:SovereignOS_Clio_Sync/implementation_plans" "$LOCAL_INBOX/implementation_plans" --fast-list --max-depth 1 --quiet || true

# 2. Pull down files from the Google Drive work_orders folder into staging
echo -e "${CYAN}[➔] Pulling new work orders and specs from Spark queue into staging...${NC}"
if rclone copy "$GDRIVE_SOURCE_SPARK" "$WO_STAGING" \
    --drive-export-formats txt \
    --max-age 24h \
    --exclude "*[Mm]ashup*" \
    --exclude "archive/**" \
    --exclude "spark/**" \
    --max-depth 1 \
    --fast-list \
    --quiet; then
    echo -e "${GREEN}[✔] Spark work_orders queue downloaded to staging.${NC}"
else
    echo -e "${RED}[❌] Failed to pull from Spark queue. Check Tailscale proxy or rclone credentials.${NC}"
    exit 1
fi

# 3. Pull root drops: Work orders to staging, docs to inbox
echo -e "${CYAN}[➔] Checking Google Drive root for work orders and tagged documents...${NC}"
rclone copy "sovereign_os:" "$WO_STAGING" \
    --drive-export-formats txt \
    --max-age 24h \
    --exclude "*[Mm]ashup*" \
    --include "WO-*" \
    --include "WO_*" \
    --max-depth 1 \
    --fast-list \
    --quiet || true

rclone copy "sovereign_os:" "$LOCAL_INBOX" \
    --drive-export-formats txt \
    --include "SOW_*" \
    --include "REQ_*" \
    --include "REPORT_*" \
    --include "EXECUTIVE_BRIEF_*" \
    --include "KB*" \
    --max-depth 1 \
    --fast-list \
    --quiet || true

# 4. Ingest work orders directly into GitOps queue (convert .txt to .md and move)
echo -e "${CYAN}[➔] Depositing work orders directly into GitOps queue (${QUEUE_INCOMING})...${NC}"
WO_COUNT=0
for f in "$WO_STAGING"/*; do
    [ -f "$f" ] || continue
    base=$(basename "$f")
    if [[ "$base" == *.md.txt ]]; then
        target_name="${base%.md.txt}.md"
    elif [[ "$base" == *.txt ]]; then
        target_name="${base%.txt}.md"
    elif [[ "$base" == *.md ]]; then
        target_name="$base"
    else
        target_name="$base.md"
    fi

    # Deduplication check: extract canonical ticket ID and calculate SHA-256 hash
    ticket_id=$(echo "$target_name" | grep -oiE '(WO[0-9]{5,}|WO-[0-9]{4}-[0-9]+|STRY[0-9]+|INC[0-9]+|DFCT[0-9]+|ENHC[0-9]+|REQ-[0-9]+)' | head -n 1 || true)
    if [ -z "$ticket_id" ]; then
        ticket_id=$(grep -m 30 -oiE '(WO[0-9]{5,}|WO-[0-9]{4}-[0-9]+|STRY[0-9]+|INC[0-9]+|DFCT[0-9]+|ENHC[0-9]+|REQ-[0-9]+)' "$f" 2>/dev/null | head -n 1 || true)
    fi
    [ -n "$ticket_id" ] && ticket_id=$(echo "$ticket_id" | tr '[:lower:]' '[:upper:]')

    f_hash=$(sha256sum "$f" 2>/dev/null | awk '{print $1}')

    is_duplicate=false
    # Check if file exists in queue/archive/ or executed/ by filename
    if [ -f "${QUEUE_ARCHIVE}/${target_name}" ] || [ -f "${QUEUE_EXECUTED}/${target_name}" ] || \
       [ -f "${QUEUE_ARCHIVE}/${base}" ] || [ -f "${QUEUE_EXECUTED}/${base}" ]; then
        is_duplicate=true
    fi

    # Check if canonical ticket ID matches any file in queue/archive/ or executed/
    if [ "$is_duplicate" = false ] && [ -n "$ticket_id" ]; then
        if find "${QUEUE_ARCHIVE}" "${QUEUE_EXECUTED}" -maxdepth 1 -name "*${ticket_id}*" -type f 2>/dev/null | grep -q .; then
            is_duplicate=true
        fi
    fi

    # Check if content hash matches any file in queue/archive/
    if [ "$is_duplicate" = false ] && [ -n "$f_hash" ]; then
        if find "${QUEUE_ARCHIVE}" -maxdepth 1 -type f -exec sha256sum {} + 2>/dev/null | grep -q "^${f_hash} "; then
            is_duplicate=true
        fi
    fi

    if [ "$is_duplicate" = true ]; then
        echo -e "${YELLOW}  [DEDUP SKIP] ${target_name} (ticket: ${ticket_id:-N/A}) already in archive/executed. Moved directly to executed/.${NC}"
        log_sync_event "dedup_skip" "[DEDUP SKIP] $target_name moved to executed/ (archived/duplicate)."
        mv -f "$f" "${QUEUE_EXECUTED}/${target_name}"
        continue
    fi

    mv "$f" "${QUEUE_INCOMING}/${target_name}"
    WO_COUNT=$((WO_COUNT + 1))
    echo -e "${CYAN}  [➔] Deposited Work Order directly into Queue: ${target_name}${NC}"
done

if [ "$WO_COUNT" -gt 0 ]; then
    echo -e "${GREEN}[✔] Deposited $WO_COUNT work order(s) directly into queue/incoming/.${NC}"
fi

# 5. Convert plain text exports (.txt / .md.txt) to .md in inbox for documentation files
CONVERT_COUNT=0
for f in "$LOCAL_INBOX"/*.txt; do
    if [ -f "$f" ]; then
        if [[ "$f" == *.md.txt ]]; then
            target_name="${f%.md.txt}.md"
        else
            target_name="${f%.txt}.md"
        fi
        mv "$f" "$target_name"
        CONVERT_COUNT=$((CONVERT_COUNT + 1))
        echo -e "${CYAN}  [➔] Converted documentation: $(basename "$f") -> $(basename "$target_name")${NC}"
    fi
done

if [ "$CONVERT_COUNT" -gt 0 ]; then
    echo -e "${GREEN}[✔] Converted $CONVERT_COUNT documentation file(s) to Markdown.${NC}"
fi

# 6. Fire Decision Derby exclusively for walkthroughs, reports, and knowledge base files
if [ -f "$DECISION_DERBY_SCRIPT" ]; then
    echo -e "${CYAN}[*] Activating Semantic Decision Derby for documentation routing...${NC}"
    "$VENV_PYTHON" "$DECISION_DERBY_SCRIPT"
    echo -e "${GREEN}[✔] Decision Derby pass complete.${NC}"
else
    echo -e "${RED}[❌] Decision Derby script missing at $DECISION_DERBY_SCRIPT${NC}"
    exit 1
fi

# 7. Archive processed items in Spark work_orders queue and root drops
echo -e "${CYAN}[➔] Archiving processed cloud files in Spark work_orders queue...${NC}"
rclone move "$GDRIVE_SOURCE_SPARK" "$GDRIVE_ARCHIVE" \
    --exclude "archive/**" \
    --exclude "spark/**" \
    --max-depth 1 \
    --fast-list \
    --quiet || true

echo -e "${CYAN}[➔] Archiving processed root work orders from Google Drive root...${NC}"
rclone move "sovereign_os:" "$GDRIVE_ARCHIVE" \
    --filter "- SovereignOS_Clio_Sync/**" \
    --filter "+ WO-*" \
    --filter "+ WO_*" \
    --filter "- *" \
    --max-depth 1 \
    --fast-list \
    --quiet || true

echo -e "${GREEN}=== Sovereign OS Pull Sync Complete ===${NC}"
log_sync_event "success" "Sovereign pull sync pass completed successfully."
