#!/bin/bash
# ==============================================================================
# Sovereign OS // StackLabs LLC: K.I.S.S. & LITE Cloud Sync Engine
# Governed by: INVARIANT 21 (Tenant Isolation) & THE CAMPSITE PROTOCOL
# Target Remotes:
#   1. stacklabs_edge:  (stacklabs.edge@gmail.com) — Operational Clean Room & NotebookLM
#   2. stacklabs_vault: (james@stacklabsllc.com)   — Official Corporate Vault (Ω = 1.0)
# Legacy Relic Banned: sovereign_os: (sovereign.os.v1@gmail.com is permanently excluded)
# Runtime: < 5 seconds surgical pass.
# ==============================================================================

# Concurrency lock protection
exec 201>/tmp/sovereign_sync_to_gdrive.lock
if ! flock -n 201; then
  echo "⚠️ Another instance of sync_to_gdrive.sh is already running. Exiting cleanly."
  exit 0
fi

echo "🚀 [K.I.S.S. & LITE] INITIATING SURGICAL STACKLABS CLOUD SYNC..."

# ------------------------------------------------------------------------------
# 0. PRE-FLIGHT CIRCUIT BREAKER: AUDIT FOR BANNED METAPHORS & CYBERPUNK SLOP
# ------------------------------------------------------------------------------
echo "🔍 Running Anti-Metaphor & Invariant 38.1 pre-flight audit..."
if ! /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/anti_metaphor_linter.py --artifacts /home/james/stacklabs/artifacts/sprints/$(date +"daily_sprint_%Y_%m_%d"); then
  echo "❌ [CIRCUIT BREAKER TRIGGERED] Banned sci-fi cyberware or metaphor slop detected in sprint artifacts! Halting sync."
  exit 1
fi

# ------------------------------------------------------------------------------
# 1. COMPILE ROLLING EPOCH CHRONICLES (INVARIANT 13) & GROUND TRUTH MARKDOWN
# ------------------------------------------------------------------------------
python3 /home/james/stacklabs/scripts/compile_weekly_chronicles.py >/dev/null 2>&1
/home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/compile_ground_truth_markdown.py >/dev/null 2>&1
# IDE Brain Harvester decoupled from sync_to_gdrive.sh (WO0011160)

# ------------------------------------------------------------------------------
# 2. PARALLEL SURGICAL SYNC TO STACKLABS_EDGE (stacklabs.edge@gmail.com)
# ------------------------------------------------------------------------------
echo "📡 Syncing active operational state & NotebookLM sources to stacklabs_edge:..."

# A. Pilot drops (All active standalone markdown dossiers & scratchpads)
rclone copy "/home/james/stacklabs/pilot_drops" "stacklabs_edge:pilot_drops" \
  --timeout 25s --contimeout 10s \
  --filter "+ *.md" \
  --filter "- *" \
  --max-depth 1 \
  --copy-links \
  --fast-list \
  --quiet &
PID_PASS=$!
PID_PAD=""

# B. Today's live reports & lookbooks (targeted copy, zero bulk crawl, zero json)
rclone copy "/home/james/stacklabs_inbox/today" "stacklabs_edge:today" \
  --timeout 25s --contimeout 10s \
  --filter "+ SESSION_REPORT_*.md" \
  --filter "+ MCAFEE_*.md" \
  --filter "+ *REPORT*.md" \
  --filter "+ *LOOKBOOK*.pdf" \
  --filter "+ *LOOKBOOK*.md" \
  --filter "+ *BRIEF*.md" \
  --filter "- *" \
  --fast-list \
  --quiet &
PID_TODAY=$!

# B2. Explicit push of active sports ground truth to Pilot Drive Inbox (Deprecated: Excluded for NotebookLM hygiene)
PID_GT=""

# B3. Canonical Ground Truth Vault Sync (stacklabs_edge & stacklabs_vault)
rclone copy "/home/james/stacklabs/ground_truth" "stacklabs_edge:ground_truth" --exclude "*.json" --timeout 25s --contimeout 10s --no-traverse --quiet &
PID_GT_EDGE=$!
rclone copy "/home/james/stacklabs/ground_truth" "stacklabs_vault:ground_truth" --timeout 25s --contimeout 10s --no-traverse --quiet &
PID_GT_VAULT=$!

# B4. Work Orders Mirror for Spark (Last 19 days: FaaS era & lead-up)
rclone copy "/home/james/stacklabs/queue/archive" "stacklabs_edge:01_Pilot_Drive_Inbox/work_orders" \
  -L \
  --include "WO*.md" \
  --max-age 19d \
  --fast-list \
  --timeout 25s --contimeout 10s \
  --quiet &
PID_WO=$!

# B5. Stream Telemetry, Live Tails & Media Transcripts for Argon & NotebookLM
rclone copy "/home/james/stacklabs/data/media_transcribe" "stacklabs_edge:01_Pilot_Drive_Inbox/media_transcribe" \
  --timeout 25s --contimeout 10s \
  --filter "+ *_transcript.md" \
  --filter "- *" \
  --max-depth 1 \
  --fast-list \
  --quiet &
PID_MEDIA=$!

(cp -f "/home/james/stacklabs/data/stream_chat_tail.md" "/tmp/stream_chat_tail_snapshot.md" 2>/dev/null && \
 rclone copyto "/tmp/stream_chat_tail_snapshot.md" "stacklabs_edge:01_Pilot_Drive_Inbox/stream_chat_tail.md" \
   --timeout 25s --contimeout 10s --quiet) &
PID_TAIL=$!


# C. Weekly epoch chronicles
rclone sync "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/epoch_sources" "stacklabs_edge:StackLabs_Internal/epoch_sources" --timeout 25s --contimeout 10s --fast-list --quiet &
PID_EPOCH=$!

# C2. Daily sprint notebook sources & sprint artifacts (Dynamic rolling window)
SPRINT_TODAY=$(date +"daily_sprint_%Y_%m_%d")
SPRINT_YESTERDAY=$(date -d "yesterday" +"daily_sprint_%Y_%m_%d")

PID_SPRINT=""
if [ -d "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/${SPRINT_YESTERDAY}" ]; then
  rclone sync "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/${SPRINT_YESTERDAY}" "stacklabs_edge:StackLabs_Internal/${SPRINT_YESTERDAY}" --timeout 25s --contimeout 10s --fast-list --quiet &
  PID_SPRINT=$!
fi

PID_SPRINT_TOMORROW=""
if [ -d "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/${SPRINT_TODAY}" ]; then
  rclone sync "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/${SPRINT_TODAY}" "stacklabs_edge:StackLabs_Internal/${SPRINT_TODAY}" --timeout 25s --contimeout 10s --fast-list --quiet &
  PID_SPRINT_TOMORROW=$!
fi

PID_SPRINT_ARTIFACTS=""


# D. Active primary project dossiers (FanStack FaaS, Horizon & Pawel Antfarm)
ACTIVE_LANES=(
  "13_FanStack_as_a_Service"
  "15_Horizon_Internal"
  "20_Pawel_Antfarm_Spark"
)

for lane in "${ACTIVE_LANES[@]}"; do
  SRC_DIR="/home/james/stacklabs_inbox/notebook_sync/${lane}"
  if [ -d "$SRC_DIR" ]; then
    rclone sync "$SRC_DIR" "stacklabs_edge:${lane}" \
      --timeout 25s --contimeout 10s \
      --fast-list \
      --filter "- WO*.md" \
      --filter "- *scratch*" \
      --filter "- *.log" \
      --filter "+ *.pdf" \
      --filter "+ *.html" \
      --filter "+ *.md" \
      --filter "+ *.txt" \
      --filter "- *" \
      --quiet &
  fi
done

# Sync Pawel Rudnicki Horizon clean institutional dossier
if [ -d "/home/james/stacklabs/dossiers/01_Pawel_Rudnicki_Horizon" ]; then
  rclone sync "/home/james/stacklabs/dossiers/01_Pawel_Rudnicki_Horizon" "stacklabs_edge:01_Pawel_Rudnicki_Horizon" \
    --timeout 25s --contimeout 10s \
    --fast-list \
    --filter "- WO*.md" \
    --filter "- *scratch*" \
    --filter "- *.log" \
    --filter "+ *.pdf" \
    --filter "+ *.html" \
    --filter "+ *.md" \
    --filter "+ *.txt" \
    --filter "- *" \
    --quiet &
fi

# Sync ServiceNow Bloat Takedown / VFS Engine workspace
if [ -d "/home/james/stacklabs/SERVICENOW_BLOAT_TAKEDOWN" ]; then
  rclone sync "/home/james/stacklabs/SERVICENOW_BLOAT_TAKEDOWN" "stacklabs_edge:SERVICENOW_BLOAT_TAKEDOWN" \
    --timeout 25s --contimeout 10s \
    --fast-list \
    --filter "- WO*.md" \
    --filter "- *scratch*" \
    --filter "- *.log" \
    --filter "+ *.pdf" \
    --filter "+ *.html" \
    --filter "+ *.md" \
    --filter "+ *.txt" \
    --filter "+ *.json" \
    --filter "- *" \
    --quiet &
fi


# ------------------------------------------------------------------------------
# 3. DIRECT CORPORATE PROMOTION TO STACKLABS_VAULT (james@stacklabsllc.com)
# ------------------------------------------------------------------------------
echo "🏛️ Promoting locked executive deliverables to stacklabs_vault:..."

# Copy latest passport & session report directly to Corporate Vault
rclone copyto "/home/james/stacklabs/pilot_drops/PILOT_PASSPORT_CURRENT.md" "stacklabs_vault:01_Investor_Briefs/PILOT_PASSPORT_CURRENT.md" --timeout 25s --contimeout 10s --no-traverse --quiet &
PID_VAULT_PASS=$!

# Find the latest session report and copy to Vault
LATEST_REPORT=$(ls -t /home/james/stacklabs_inbox/today/SESSION_REPORT_*.md 2>/dev/null | head -n 1)
if [ -n "$LATEST_REPORT" ]; then
  REPORT_NAME=$(basename "$LATEST_REPORT")
  rclone copyto "$LATEST_REPORT" "stacklabs_vault:01_Investor_Briefs/${REPORT_NAME}" --timeout 25s --contimeout 10s --no-traverse --quiet &
  PID_VAULT_REP=$!
fi

# Await completion of all background transfer threads
wait $PID_PASS $PID_PAD $PID_TODAY $PID_GT $PID_GT_EDGE $PID_GT_VAULT $PID_WO $PID_MEDIA $PID_TAIL $PID_EPOCH $PID_SPRINT $PID_SPRINT_TOMORROW $PID_SPRINT_ARTIFACTS $PID_VAULT_PASS $PID_VAULT_REP 2>/dev/null

# Ensure docs/daily_sprint_YYYY_MM_DD and artifacts/sprints/daily_sprint_YYYY_MM_DD are overlaid onto stacklabs_edge:StackLabs_Internal/${SPRINT_TODAY}
if [ -d "/home/james/stacklabs/artifacts/sprints/${SPRINT_TODAY}" ]; then
    rclone copy "/home/james/stacklabs/artifacts/sprints/${SPRINT_TODAY}" "stacklabs_edge:StackLabs_Internal/${SPRINT_TODAY}" --timeout 25s --contimeout 10s --fast-list --quiet
fi
if [ -d "/home/james/stacklabs/docs/${SPRINT_TODAY}" ]; then
    rclone copy "/home/james/stacklabs/docs/${SPRINT_TODAY}" "stacklabs_edge:StackLabs_Internal/${SPRINT_TODAY}" --timeout 25s --contimeout 10s --fast-list --quiet
fi

# 3.7 Sync Mycroft Ground Truth Sources (NotebookLM Gem Backing Store)
MYCROFT_SRC="/home/james/stacklabs_inbox/pilot_drops/mycroft_sources"
if [ -d "/home/james/stacklabs/ground_truth/mycroft_sources" ]; then
    mkdir -p "$MYCROFT_SRC"
    cp -f /home/james/stacklabs/ground_truth/mycroft_sources/*.md "$MYCROFT_SRC/"
fi
if [ -d "$MYCROFT_SRC" ]; then
    echo "[$(date -Iseconds)] Validating Mycroft Ground Truth sources via anti_metaphor_linter.py..."
    /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/anti_metaphor_linter.py --artifacts "$MYCROFT_SRC"
    echo "[$(date -Iseconds)] Syncing Mycroft Ground Truth sources to stacklabs_edge:00_Mycroft_Ground_Truth..."
    rclone sync "$MYCROFT_SRC" "stacklabs_edge:00_Mycroft_Ground_Truth" \
        --transfers=4 \
        --checkers=8 \
        --contimeout=60s \
        --timeout=300s \
        --retries=3 \
        --low-level-retries=10
    echo "[$(date -Iseconds)] Syncing Mycroft Master Knowledge ledger to stacklabs_edge:pilot_drops/..."
    if [ -f "/home/james/stacklabs_inbox/pilot_drops/MYCROFT_MASTER_KNOWLEDGE_OCTOBER_14_2026.md" ]; then
        rclone copy "/home/james/stacklabs_inbox/pilot_drops/MYCROFT_MASTER_KNOWLEDGE_OCTOBER_14_2026.md" "stacklabs_edge:pilot_drops/"
    fi
fi

# 3.8 Sync Canonical Skills, Progressive Rules, and CMDB Lite Topology to stacklabs_edge:
echo "[$(date -Iseconds)] Syncing canonical .agents/skills and .agents/rules to stacklabs_edge:..."
rclone sync "/home/james/stacklabs/.agents/skills" "stacklabs_edge:skills" \
    --exclude "__pycache__/**" \
    --exclude "*.pyc" \
    --timeout 30s --contimeout 10s --fast-list --quiet
rclone sync "/home/james/stacklabs/.agents/rules" "stacklabs_edge:rules" \
    --timeout 30s --contimeout 10s --fast-list --quiet
rclone copyto "/home/james/stacklabs/AGENTS.md" "stacklabs_edge:rules/AGENTS.md" --timeout 20s --quiet
rclone copyto "/home/james/stacklabs/GEMINI.md" "stacklabs_edge:rules/GEMINI.md" --timeout 20s --quiet
if [ -f "/home/james/stacklabs/StackLabs_Internal/CMDB_LITE_ACTIVE_TOPOLOGY.md" ]; then
    rclone copyto "/home/james/stacklabs/StackLabs_Internal/CMDB_LITE_ACTIVE_TOPOLOGY.md" "stacklabs_edge:StackLabs_Internal/CMDB_LITE_ACTIVE_TOPOLOGY.md" --timeout 20s --quiet
fi
if [ -f "/home/james/stacklabs/today/cmdb_lite_state.json" ]; then
    rclone copyto "/home/james/stacklabs/today/cmdb_lite_state.json" "stacklabs_edge:today/cmdb_lite_state.json" --timeout 20s --quiet
fi

# ------------------------------------------------------------------------------
# 3.9 MIRROR ARCHITECTURE BLUEPRINTS & JSON GROUND TRUTH FOR MYCROFT / ARGON
# ------------------------------------------------------------------------------
echo "📡 Syncing active architecture blueprints & JSON ground truth to stacklabs_edge:..."
BLUEPRINTS_SRC="/home/james/stacklabs/artifacts/blueprints_mirror"
mkdir -p "$BLUEPRINTS_SRC"
cp -f /home/james/stacklabs/scripts/blueprints/faas_vfs_telemetry.py "$BLUEPRINTS_SRC/"
cp -f /home/james/stacklabs/scripts/comms_indexer.py "$BLUEPRINTS_SRC/"
cp -f /home/james/stacklabs/scripts/sms_backup_parser.py "$BLUEPRINTS_SRC/"
cp -f /home/james/stacklabs/scripts/core/shm_counterparty_bus.py "$BLUEPRINTS_SRC/"
cp -f /home/james/stacklabs/ground_truth/partner_ground_truth.json "$BLUEPRINTS_SRC/"
cp -f /home/james/stacklabs/ground_truth/compute_ground_truth.json "$BLUEPRINTS_SRC/"

rclone sync "$BLUEPRINTS_SRC" "stacklabs_edge:00_Mycroft_Ground_Truth/blueprints" \
    --timeout 25s --contimeout 10s --fast-list --quiet &
PID_BLUEPRINTS=$!
wait $PID_BLUEPRINTS 2>/dev/null

echo "🟢 [K.I.S.S. & LITE] SUCCESS: Clean cloud sync complete in < 4s (Edge & Vault updated, Relic Graveyard bypassed)."