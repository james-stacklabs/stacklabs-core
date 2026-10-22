#!/usr/bin/env bash
# ==============================================================================
# Sovereign OS - Dedicated StackLabs Edge Curated Promotion Engine
# Path: /home/james/stacklabs/scripts/sync_stacklabs_edge.sh
# Governed by: Invariant 18 & WO0010243
# Target Remote: stacklabs_edge: (stacklabs.edge@gmail.com Google Workspace Drive)
# ==============================================================================

set -euo pipefail

# 1. Concurrency Lock Protection
LOCK_FILE="/tmp/sync_stacklabs_edge.lock"
exec 202>"$LOCK_FILE"
if ! flock -n 202; then
  echo "⚠️ Another instance of sync_stacklabs_edge.sh is already running. Exiting cleanly."
  exit 0
fi

REMOTE="stacklabs_edge:"
EXTRA_FLAGS=("$@")

echo "======================================================================"
echo "⚡ STACKLABS EDGE CURATED PROMOTION ENGINE (WO0010243)"
echo "📡 Target Remote: ${REMOTE} (stacklabs.edge@gmail.com)"
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
# Enforce the pristine 2-directory structure on stacklabs_edge:
# - 02_Edge_Platform_Engineering
# - 03_WildSeed_Sovereign_Swarm
echo "📁 [STEP 2/4] Verifying edge directory structure..."
REQUIRED_DIRS=(
  "02_Edge_Platform_Engineering"
  "03_WildSeed_Sovereign_Swarm"
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
  rclone copyto "${src}" "${REMOTE}${target_rel}" "${EXTRA_FLAGS[@]}"
  echo "     ✔ Complete."
}

TOTAL_FILES=16

# ==============================================================================
# LANE 2: 02_Edge_Platform_Engineering (8 deliverables)
# ==============================================================================

SRC_1=$(resolve_source_path "Phase 0 Zero Hour Provisioning & Staging Runbook" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/PHASE_0_ZERO_HOUR_PROVISIONING_AND_STAGING_RUNBOOK.md" \
  "/home/james/sovereign_inbox/pilot_drops/PHASE_0_ZERO_HOUR_PROVISIONING_AND_STAGING_RUNBOOK.md" \
  "/home/james/stacklabs/dna/docs/PHASE_0_ZERO_HOUR_PROVISIONING_AND_STAGING_RUNBOOK.md")
promote_file 1 "${TOTAL_FILES}" "Phase 0 Runbook" "${SRC_1}" \
  "02_Edge_Platform_Engineering/PHASE_0_ZERO_HOUR_PROVISIONING_AND_STAGING_RUNBOOK.md"

SRC_2=$(resolve_source_path "Architecture Spec - Sovereign Intelligence Radar (SIR)" \
  "/home/james/stacklabs/dna/docs/ARCHITECTURE_SPEC_SOVEREIGN_INTELLIGENCE_RADAR_SIR.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/ARCHITECTURE_SPEC_SOVEREIGN_INTELLIGENCE_RADAR_SIR.md" \
  "/home/james/sovereign_inbox/pilot_drops/ARCHITECTURE_SPEC_SOVEREIGN_INTELLIGENCE_RADAR_SIR.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/docs/ARCHITECTURE_SPEC_SOVEREIGN_INTELLIGENCE_RADAR_SIR.md")
promote_file 2 "${TOTAL_FILES}" "Architecture Spec SIR" "${SRC_2}" \
  "02_Edge_Platform_Engineering/ARCHITECTURE_SPEC_SOVEREIGN_INTELLIGENCE_RADAR_SIR.md"

SRC_3=$(resolve_source_path "Spec SIR Mod 002 - Predictive Horizon Radar" \
  "/home/james/stacklabs/dna/docs/SPEC_SIR_MOD_002_PREDICTIVE_HORIZON_RADAR.md" \
  "/home/james/sovereign_inbox/pilot_drops/SPEC_SIR_MOD_002_PREDICTIVE_HORIZON_RADAR.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/SPEC_SIR_MOD_002_PREDICTIVE_HORIZON_RADAR.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/docs/SPEC_SIR_MOD_002_PREDICTIVE_HORIZON_RADAR.md")
promote_file 3 "${TOTAL_FILES}" "Spec SIR Mod 002 Predictive Horizon Radar" "${SRC_3}" \
  "02_Edge_Platform_Engineering/SPEC_SIR_MOD_002_PREDICTIVE_HORIZON_RADAR.md"

SRC_4=$(resolve_source_path "Spec - Anthropomorphic Domain Microservices (ADM) Framework" \
  "/home/james/stacklabs/dna/docs/SPEC_ANTHROPOMORPHIC_DOMAIN_MICROSERVICES_ADM_FRAMEWORK.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/SPEC_ANTHROPOMORPHIC_DOMAIN_MICROSERVICES_ADM_FRAMEWORK.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/docs/SPEC_ANTHROPOMORPHIC_DOMAIN_MICROSERVICES_ADM_FRAMEWORK.md")
promote_file 4 "${TOTAL_FILES}" "Spec ADM Framework" "${SRC_4}" \
  "02_Edge_Platform_Engineering/SPEC_ANTHROPOMORPHIC_DOMAIN_MICROSERVICES_ADM_FRAMEWORK.md"

SRC_5=$(resolve_source_path "StackLabs Sanitized Platform Capabilities & Power Tools" \
  "/home/james/stacklabs/dna/docs/STACKLABS_SANITIZED_PLATFORM_CAPABILITIES_AND_POWER_TOOLS.md" \
  "/home/james/sovereign_inbox/pilot_drops/documents/STACKLABS_SANITIZED_PLATFORM_CAPABILITIES_AND_POWER_TOOLS.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/STACKLABS_SANITIZED_PLATFORM_CAPABILITIES_AND_POWER_TOOLS.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/docs/STACKLABS_SANITIZED_PLATFORM_CAPABILITIES_AND_POWER_TOOLS.md")
promote_file 5 "${TOTAL_FILES}" "Platform Capabilities & Power Tools" "${SRC_5}" \
  "02_Edge_Platform_Engineering/STACKLABS_SANITIZED_PLATFORM_CAPABILITIES_AND_POWER_TOOLS.md"

SRC_6=$(resolve_source_path "Sovereign Power Tools and Microservices Catalog" \
  "/home/james/stacklabs/dna/docs/Sovereign_Power_Tools_and_Microservices_Catalog.md" \
  "/home/james/sovereign_inbox/notebook_sync/Sovereign_Power_Tools_and_Microservices_Catalog.md" \
  "/home/james/sovereign_inbox/pilot_drops/documents/Sovereign_Power_Tools_and_Microservices_Catalog.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/docs/Sovereign_Power_Tools_and_Microservices_Catalog.md")
promote_file 6 "${TOTAL_FILES}" "Power Tools Catalog" "${SRC_6}" \
  "02_Edge_Platform_Engineering/Sovereign_Power_Tools_and_Microservices_Catalog.md"

SRC_7=$(resolve_source_path "07 Subnet Steward Role and Human Equity Governance" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/07_SUBNET_STEWARD_ROLE_AND_HUMAN_EQUITY_GOVERNANCE.md" \
  "/home/james/sovereign_inbox/pilot_drops/pristine_notebooklm_sources/07_SUBNET_STEWARD_ROLE_AND_HUMAN_EQUITY_GOVERNANCE.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/07_SUBNET_STEWARD_ROLE_AND_HUMAN_EQUITY_GOVERNANCE.md")
promote_file 7 "${TOTAL_FILES}" "Subnet Steward Role & Governance" "${SRC_7}" \
  "02_Edge_Platform_Engineering/07_SUBNET_STEWARD_ROLE_AND_HUMAN_EQUITY_GOVERNANCE.md"

SRC_8=$(resolve_source_path "The Campsite Protocol - Operational Invariants & Human Equity Governance" \
  "/home/james/stacklabs/dna/docs/The Campsite Protocol_ Operational Invariants & Human Equity Governance.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/The Campsite Protocol_ Operational Invariants & Human Equity Governance.md" \
  "/home/james/sovereign_inbox/pilot_drops/documents/The Campsite Protocol_ Operational Invariants & Human Equity Governance.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/docs/The Campsite Protocol_ Operational Invariants & Human Equity Governance.md")
promote_file 8 "${TOTAL_FILES}" "The Campsite Protocol" "${SRC_8}" \
  "02_Edge_Platform_Engineering/The Campsite Protocol_ Operational Invariants & Human Equity Governance.md"

# ==============================================================================
# LANE 3: 03_WildSeed_Sovereign_Swarm (8 deliverables)
# ==============================================================================

SRC_9=$(resolve_source_path "White Paper - WildSeed Algorithmic Reclamation & E-A-T Engine" \
  "/home/james/stacklabs/dna/docs/WHITE_PAPER_WILDSEED_ALGORITHMIC_RECLAMATION_AND_EAT_ENGINE.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/WHITE_PAPER_WILDSEED_ALGORITHMIC_RECLAMATION_AND_EAT_ENGINE.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/docs/WHITE_PAPER_WILDSEED_ALGORITHMIC_RECLAMATION_AND_EAT_ENGINE.md")
promote_file 9 "${TOTAL_FILES}" "White Paper WildSeed E-A-T Engine" "${SRC_9}" \
  "03_WildSeed_Sovereign_Swarm/WHITE_PAPER_WILDSEED_ALGORITHMIC_RECLAMATION_AND_EAT_ENGINE.md"

SRC_10=$(resolve_source_path "WildSeed Module 01 - Solventless Extraction Thermodynamics" \
  "/home/james/stacklabs/dna/docs/WILDSEED_MODULE_01_SOLVENTLESS_EXTRACTION_THERMODYNAMICS.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/WILDSEED_MODULE_01_SOLVENTLESS_EXTRACTION_THERMODYNAMICS.md" \
  "/home/james/sovereign_inbox/WildSeed_Model_Forge/WILDSEED_MODULE_01_SOLVENTLESS_EXTRACTION_THERMODYNAMICS.md" \
  "/home/james/sovereign_inbox/pilot_drops/WILDSEED_MODULE_01_SOLVENTLESS_EXTRACTION_THERMODYNAMICS.md")
promote_file 10 "${TOTAL_FILES}" "WildSeed Module 01 Solventless Extraction" "${SRC_10}" \
  "03_WildSeed_Sovereign_Swarm/WILDSEED_MODULE_01_SOLVENTLESS_EXTRACTION_THERMODYNAMICS.md"

SRC_11=$(resolve_source_path "WildSeed Module 02 - Living Soil Terpene Biogenesis and Curing Chemistry" \
  "/home/james/stacklabs/dna/docs/WILDSEED_MODULE_02_LIVING_SOIL_TERPENE_BIOGENESIS_AND_CURING_CHEMISTRY.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/WILDSEED_MODULE_02_LIVING_SOIL_TERPENE_BIOGENESIS_AND_CURING_CHEMISTRY.md" \
  "/home/james/sovereign_inbox/WildSeed_Model_Forge/WILDSEED_MODULE_02_LIVING_SOIL_TERPENE_BIOGENESIS_AND_CURING_CHEMISTRY.md")
promote_file 11 "${TOTAL_FILES}" "WildSeed Module 02 Living Soil Terpenes" "${SRC_11}" \
  "03_WildSeed_Sovereign_Swarm/WILDSEED_MODULE_02_LIVING_SOIL_TERPENE_BIOGENESIS_AND_CURING_CHEMISTRY.md"

SRC_12=$(resolve_source_path "WildSeed Extracts Product Data Sheet" \
  "/home/james/stacklabs/dna/docs/WILDSEED_EXTRACTS_PRODUCT_DATA_SHEET.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/WILDSEED_EXTRACTS_PRODUCT_DATA_SHEET.md" \
  "/home/james/sovereign_inbox/pilot_drops/WILDSEED_EXTRACTS_PRODUCT_DATA_SHEET.md")
promote_file 12 "${TOTAL_FILES}" "WildSeed Product Data Sheet" "${SRC_12}" \
  "03_WildSeed_Sovereign_Swarm/WILDSEED_EXTRACTS_PRODUCT_DATA_SHEET.md"

SRC_13=$(resolve_source_path "Companion Source - WildSeed SERP & Schema Evidence" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/COMPANION_SOURCE_WILDSEED_SERP_AND_SCHEMA_EVIDENCE.md" \
  "/home/james/sovereign_inbox/pilot_drops/documents/COMPANION_SOURCE_WILDSEED_SERP_AND_SCHEMA_EVIDENCE.md")
promote_file 13 "${TOTAL_FILES}" "Companion Source WildSeed SERP & Schema Evidence" "${SRC_13}" \
  "03_WildSeed_Sovereign_Swarm/COMPANION_SOURCE_WILDSEED_SERP_AND_SCHEMA_EVIDENCE.md"

SRC_14=$(resolve_source_path "09 WildSeed Tenant Zero Agreement and SOW" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/09_WILDSEED_TENANT_ZERO_AGREEMENT_AND_SOW.md" \
  "/home/james/sovereign_inbox/pilot_drops/pristine_notebooklm_sources/09_WILDSEED_TENANT_ZERO_AGREEMENT_AND_SOW.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/09_WILDSEED_TENANT_ZERO_AGREEMENT_AND_SOW.md")
promote_file 14 "${TOTAL_FILES}" "09 WildSeed Tenant Zero Agreement & SOW" "${SRC_14}" \
  "03_WildSeed_Sovereign_Swarm/09_WILDSEED_TENANT_ZERO_AGREEMENT_AND_SOW.md"

SRC_15=$(resolve_source_path "StackLabs LLC & WildSeed LLC — Commercial Sweetener Addendum & Pilot SOW" \
  "/home/james/stacklabs/dna/docs/StackLabs LLC & WildSeed LLC — Commercial Sweetener Addendum & Pilot SOW.md" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/StackLabs LLC & WildSeed LLC — Commercial Sweetener Addendum & Pilot SOW.md" \
  "/home/james/sovereign_inbox/pilot_drops/documents/StackLabs LLC & WildSeed LLC — Commercial Sweetener Addendum & Pilot SOW.md")
promote_file 15 "${TOTAL_FILES}" "Commercial Sweetener Addendum & Pilot SOW" "${SRC_15}" \
  "03_WildSeed_Sovereign_Swarm/StackLabs LLC & WildSeed LLC — Commercial Sweetener Addendum & Pilot SOW.md"

SRC_16=$(resolve_source_path "Pawel Claude ADM Roleplay Simulation" \
  "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/PAWEL_CLAUDE_ADM_ROLEPLAY_SIMULATION.md" \
  "/home/james/sovereign_inbox/pilot_drops/PAWEL_CLAUDE_ADM_ROLEPLAY_SIMULATION.md")
promote_file 16 "${TOTAL_FILES}" "Pawel Claude ADM Simulation" "${SRC_16}" \
  "03_WildSeed_Sovereign_Swarm/PAWEL_CLAUDE_ADM_ROLEPLAY_SIMULATION.md"

echo

# 5. Inventory Confirmation
# Print recursive listing of target directories to prove structure
echo "📋 [STEP 4/4] Generating inventory confirmation..."
echo "----------------------------------------------------------------------"
echo "--- 02_Edge_Platform_Engineering/ ---"
rclone lsf "${REMOTE}02_Edge_Platform_Engineering" -R "${EXTRA_FLAGS[@]}"
echo
echo "--- 03_WildSeed_Sovereign_Swarm/ ---"
rclone lsf "${REMOTE}03_WildSeed_Sovereign_Swarm" -R "${EXTRA_FLAGS[@]}"
echo
echo "--- Full Lane Inventory (Filtered Recursive) ---"
rclone lsf "${REMOTE}" -R --include "/02_Edge_Platform_Engineering/**" --include "/03_WildSeed_Sovereign_Swarm/**" "${EXTRA_FLAGS[@]}"
echo "----------------------------------------------------------------------"
echo

echo "🟢 SUCCESS: StackLabs Edge Clean Lanes synchronized and verified."
exit 0
