#!/usr/bin/env bash
# ==============================================================================
# Sovereign OS - Dedicated StackLabs Corporate Vault Curated Promotion Engine
# Path: /home/james/stacklabs/scripts/sync_stacklabs_vault.sh
# Governed by: Invariant 18 & WO0010218 / WO0010220
# Target Remote: stacklabs_vault: (james@stacklabsllc.com Google Workspace Drive)
# ==============================================================================

set -euo pipefail

# 1. Concurrency Lock Protection
LOCK_FILE="/tmp/sync_stacklabs_vault.lock"
exec 202>"$LOCK_FILE"
if ! flock -n 202; then
  echo "⚠️ Another instance of sync_stacklabs_vault.sh is already running. Exiting cleanly."
  exit 0
fi

REMOTE="stacklabs_vault:"
EXTRA_FLAGS=("$@")

echo "======================================================================"
echo "🏦 STACKLABS CORPORATE VAULT CURATED PROMOTION ENGINE (WO0010220)"
echo "📡 Target Remote: ${REMOTE} (james@stacklabsllc.com)"
echo "🕒 Timestamp:     $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "======================================================================"
echo

# 2. Verify Rclone Configuration and Remote Connectivity
echo "🔍 [STEP 1/4] Verifying rclone remote configuration..."
if ! command -v rclone >/dev/null 2>&1; then
  echo "❌ ERROR: rclone command not found in PATH." >&2
  exit 1
fi

if ! rclone listremotes | grep -q "^${REMOTE}$"; then
  echo "❌ ERROR: Remote '${REMOTE}' is not configured in rclone." >&2
  echo "Available remotes:"
  rclone listremotes
  exit 1
fi
echo "  ✔ Remote '${REMOTE}' confirmed configured and accessible."
echo

# 3. Directory Verification
# Enforce the pristine 4-directory structure on stacklabs_vault:
# - 01_Investor_Briefs
# - 02_Financial_Models
# - 03_CMDB_&_Hardware_Architecture
# - 04_Corporate_&_Legal
echo "📁 [STEP 2/4] Verifying corporate vault directory structure..."
REQUIRED_DIRS=(
  "01_Investor_Briefs"
  "02_Financial_Models"
  "03_CMDB_&_Hardware_Architecture"
  "04_Corporate_&_Legal"
)

for target_dir in "${REQUIRED_DIRS[@]}"; do
  # rclone mkdir ensures the remote directory exists idempotently
  rclone mkdir "${REMOTE}${target_dir}" "${EXTRA_FLAGS[@]}"
  echo "  ✔ Verified directory: ${target_dir}/"
done
echo

# 4. Curated Single-File Copies (NEVER bulk directory sync)
# Rule: Only promote explicit, curated deliverables using rclone copyto.
echo "🚀 [STEP 3/4] Promoting curated deliverables via rclone copyto..."

# Helper to find first existing file from candidates
resolve_source_path() {
  local label="$1"
  shift
  for candidate in "$@"; do
    if [ -f "$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  echo "❌ ERROR: Could not locate source file for ${label} among candidates:" >&2
  for candidate in "$@"; do
    echo "   - ${candidate}" >&2
  done
  return 1
}

promote_file() {
  local index="$1"
  local total="$2"
  local label="$3"
  local src="$4"
  local target_rel="$5"

  echo "  📄 Copying ${index}/${total}: ${label}..."
  echo "     Source: ${src}"
  echo "     Target: ${REMOTE}${target_rel}"
  rclone copyto -L "${src}" "${REMOTE}${target_rel}" "${EXTRA_FLAGS[@]}"
  echo "     ✔ Complete."
}

TOTAL_FILES=14

# --- 1. 01_Investor_Briefs ---
SRC_1=$(resolve_source_path "Executive Brief (Pawel Rudnicki)" \
  "/home/james/stacklabs/config/governance/Executive Brief - Sovereign Knot & Sentinel Governance (Pawel Rudnicki).md" \
  "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/docs/Executive Brief - Sovereign Knot & Sentinel Governance (Pawel Rudnicki).md" \
  "/home/james/stacklabs/dna/docs/Executive Brief - Sovereign Knot & Sentinel Governance (Pawel Rudnicki).md")
promote_file 1 "${TOTAL_FILES}" "Executive Brief (Pawel Rudnicki)" "${SRC_1}" \
  "01_Investor_Briefs/Executive Brief - Sovereign Knot & Sentinel Governance (Pawel Rudnicki).md"

SRC_2=$(resolve_source_path "Executive Syndicate Memo (The Sunday Napkin)" \
  "/home/james/stacklabs/config/governance/StackLabs LLC — Executive Syndicate Memo (The Sunday Napkin).md" \
  "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/docs/StackLabs LLC — Executive Syndicate Memo (The Sunday Napkin).md" \
  "/home/james/stacklabs_inbox/notebook_sync/StackLabs_External/StackLabs LLC — Executive Syndicate Memo (The Sunday Napkin).md" \
  "/home/james/stacklabs/dna/docs/StackLabs LLC — Executive Syndicate Memo (The Sunday Napkin).md")
promote_file 2 "${TOTAL_FILES}" "Executive Syndicate Memo (The Sunday Napkin)" "${SRC_2}" \
  "01_Investor_Briefs/StackLabs LLC — Executive Syndicate Memo (The Sunday Napkin).md"

SRC_3=$(resolve_source_path "Sovereign Edge & Digital Homestead Master QA Cheat Sheet" \
  "/home/james/stacklabs/config/governance/SOVEREIGN_EDGE_AND_DIGITAL_HOMESTEAD_MASTER_QA_CHEAT_SHEET.md" \
  "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/docs/SOVEREIGN_EDGE_AND_DIGITAL_HOMESTEAD_MASTER_QA_CHEAT_SHEET.md" \
  "/home/james/stacklabs/dna/docs/SOVEREIGN_EDGE_AND_DIGITAL_HOMESTEAD_MASTER_QA_CHEAT_SHEET.md")
promote_file 3 "${TOTAL_FILES}" "Master QA Cheat Sheet" "${SRC_3}" \
  "01_Investor_Briefs/SOVEREIGN_EDGE_AND_DIGITAL_HOMESTEAD_MASTER_QA_CHEAT_SHEET.md"

SRC_4=$(resolve_source_path "Sovereign Edge Audio Drill Cheatsheet" \
  "/home/james/stacklabs/config/governance/SOVEREIGN_EDGE_AUDIO_DRILL_CHEATSHEET.md" \
  "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/docs/SOVEREIGN_EDGE_AUDIO_DRILL_CHEATSHEET.md" \
  "/home/james/stacklabs/dna/docs/SOVEREIGN_EDGE_AUDIO_DRILL_CHEATSHEET.md")
promote_file 4 "${TOTAL_FILES}" "Audio Drill Cheatsheet" "${SRC_4}" \
  "01_Investor_Briefs/SOVEREIGN_EDGE_AUDIO_DRILL_CHEATSHEET.md"

SRC_5=$(resolve_source_path "Jeremy Malone Builder Moat Playbook" \
  "/home/james/stacklabs/config/governance/PLAYBOOK_2026_JEREMY_MALONE_BUILDER_MOAT.md" \
  "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/docs/PLAYBOOK_2026_JEREMY_MALONE_BUILDER_MOAT.md" \
  "/home/james/stacklabs_inbox/reports/PLAYBOOK_2026_JEREMY_MALONE_BUILDER_MOAT.md" \
  "/home/james/stacklabs/dna/docs/PLAYBOOK_2026_JEREMY_MALONE_BUILDER_MOAT.md")
promote_file 5 "${TOTAL_FILES}" "Jeremy Malone Builder Moat Playbook" "${SRC_5}" \
  "01_Investor_Briefs/PLAYBOOK_2026_JEREMY_MALONE_BUILDER_MOAT.md"

# --- 2. 02_Financial_Models ---
# Model-S hardware pro formas permanently purged per Invariant 3 (Zero Hardware Sales).

# --- 3. 03_CMDB_&_Hardware_Architecture ---
SRC_8=$(resolve_source_path "Power Tools & Microservices Catalog" \
  "/home/james/stacklabs/config/governance/Sovereign_Power_Tools_and_Microservices_Catalog.md" \
  "/home/james/stacklabs/dna/docs/Sovereign_Power_Tools_and_Microservices_Catalog.md")
promote_file 8 "${TOTAL_FILES}" "Power Tools & Microservices Catalog" "${SRC_8}" \
  "03_CMDB_&_Hardware_Architecture/Sovereign_Power_Tools_and_Microservices_Catalog.md"

SRC_9=$(resolve_source_path "Sovereign Edge Pilot Technical Architecture" \
  "/home/james/stacklabs/config/governance/SOVEREIGN_EDGE_PILOT_PROGRAM_TECHNICAL_ARCHITECTURE_AND_MONETIZATION_BLUEPRINT.md" \
  "/home/james/stacklabs/dna/docs/SOVEREIGN_EDGE_PILOT_PROGRAM_TECHNICAL_ARCHITECTURE_AND_MONETIZATION_BLUEPRINT.md")
promote_file 9 "${TOTAL_FILES}" "Sovereign Edge Pilot Blueprint" "${SRC_9}" \
  "03_CMDB_&_Hardware_Architecture/SOVEREIGN_EDGE_PILOT_PROGRAM_TECHNICAL_ARCHITECTURE_AND_MONETIZATION_BLUEPRINT.md"

SRC_10=$(resolve_source_path "Digital Homestead Davidson Homes Specification" \
  "/home/james/stacklabs/config/governance/SPEC_2026_SNC_DH_001_DIGITAL_HOMESTEAD_DAVIDSON_HOMES.md" \
  "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/docs/SPEC_2026_SNC_DH_001_DIGITAL_HOMESTEAD_DAVIDSON_HOMES.md" \
  "/home/james/stacklabs/dna/docs/SPEC_2026_SNC_DH_001_DIGITAL_HOMESTEAD_DAVIDSON_HOMES.md")
promote_file 10 "${TOTAL_FILES}" "Digital Homestead Davidson Homes Spec" "${SRC_10}" \
  "03_CMDB_&_Hardware_Architecture/SPEC_2026_SNC_DH_001_DIGITAL_HOMESTEAD_DAVIDSON_HOMES.md"

SRC_11=$(resolve_source_path "The Digital Magna Carta" \
  "/home/james/stacklabs/config/governance/THE_DIGITAL_MAGNA_CARTA.md" \
  "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/docs/THE_DIGITAL_MAGNA_CARTA.md" \
  "/home/james/stacklabs/dna/docs/THE_DIGITAL_MAGNA_CARTA.md")
promote_file 11 "${TOTAL_FILES}" "The Digital Magna Carta" "${SRC_11}" \
  "03_CMDB_&_Hardware_Architecture/THE_DIGITAL_MAGNA_CARTA.md"

# --- 4. 04_Corporate_&_Legal ---
SRC_12=$(resolve_source_path "StackLabs LLC Post-Money SAFE Agreement" \
  '/home/james/stacklabs/config/governance/StackLabs LLC — Post-Money SAFE Agreement ($125k _ $3.5M Cap).md' \
  '/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/docs/StackLabs LLC — Post-Money SAFE Agreement ($125k _ $3.5M Cap).md' \
  '/home/james/stacklabs/dna/docs/StackLabs LLC — Post-Money SAFE Agreement ($125k _ $3.5M Cap).md')
promote_file 12 "${TOTAL_FILES}" "Post-Money SAFE Agreement" "${SRC_12}" \
  '04_Corporate_&_Legal/StackLabs LLC — Post-Money SAFE Agreement ($125k _ $3.5M Cap).md'

SRC_13=$(resolve_source_path "StackLabs & WildSeed Commercial Sweetener & Pilot SOW" \
  "/home/james/stacklabs/config/governance/StackLabs LLC & WildSeed LLC — Commercial Sweetener Addendum & Pilot SOW.md" \
  "/home/james/stacklabs/dna/docs/StackLabs LLC & WildSeed LLC — Commercial Sweetener Addendum & Pilot SOW.md")
promote_file 13 "${TOTAL_FILES}" "Commercial Sweetener Addendum & Pilot SOW" "${SRC_13}" \
  "04_Corporate_&_Legal/StackLabs LLC & WildSeed LLC — Commercial Sweetener Addendum & Pilot SOW.md"

SRC_14=$(resolve_source_path "Covenant Rules of the Yard" \
  "/home/james/stacklabs/config/governance/COVENANT_2026_RULES_OF_THE_YARD.md" \
  "/home/james/stacklabs/dna/docs/COVENANT_2026_RULES_OF_THE_YARD.md")
promote_file 14 "${TOTAL_FILES}" "Covenant Rules of the Yard" "${SRC_14}" \
  "04_Corporate_&_Legal/COVENANT_2026_RULES_OF_THE_YARD.md"
echo

# 5. Inventory Confirmation
# Print recursive listing of stacklabs_vault: to prove structure
echo "📋 [STEP 4/4] Generating inventory confirmation (rclone lsf ${REMOTE} -R)..."
echo "----------------------------------------------------------------------"
rclone lsf "${REMOTE}" -R "${EXTRA_FLAGS[@]}"
echo "----------------------------------------------------------------------"
echo

echo "🟢 SUCCESS: StackLabs Corporate Vault synchronized and verified."
exit 0
