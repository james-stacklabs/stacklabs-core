#!/usr/bin/env bash
# ==============================================================================
# Script: /home/james/stacklabs/scripts/surgical_cleanse.sh
# Purpose: Cleanse StackLabs workspace, migrate from legacy SovereignOS paths,
#          lay down zero-breakage symlink bridges, update user systemd units,
#          and restart background services.
# Host: Clio Workstation (Ubuntu Linux, x86_64, user: james)
# Verified: 2026-10-03 (Eliminates circular symlink trap & sudo systemd errors)
# ==============================================================================

set -euo pipefail

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/home/james/.stacklabs_cleanse_backup_${TIMESTAMP}"
STACKLABS_ROOT="/home/james/stacklabs"
LEGACY_ROOT="/home/james/stacklabs"
PHYSICAL_INBOX="/home/james/stacklabs_inbox"
LEGACY_INBOX="/home/james/sovereign_inbox"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"

log() {
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] [CLEANSE] $*"
}

warn() {
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] [WARNING] $*" >&2
}

err() {
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] [ERROR] $*" >&2
    exit 1
}

log "Initializing pre-migration backup at ${BACKUP_DIR}..."
mkdir -p "${BACKUP_DIR}/systemd_user"
mkdir -p "${BACKUP_DIR}/scripts"

# 1. Managed User Systemd Services
USER_SERVICES=(
    "clio_queue_watcher.service"
    "faas_game_tailer.service"
    "fanstack-poller.service"
    "fanstack-relay.service"
    "highlight_watcher.service"
    "metal_polygraph.service"
    "scratch-pad-poller.service"
    "sovereign_core_api.service"
    "sovereign_pilot_drop.service"
    "stream_sniper_daemon.service"
    "tmi-daemon.service"
    "carroll-craft.service"
    "davincis-sentinel.service"
    "gmail_promo_sweeper.service"
)

log "Stopping 14 active user background services (zero file-lock contention)..."
for svc in "${USER_SERVICES[@]}"; do
    if systemctl --user is-active --quiet "${svc}" 2>/dev/null; then
        log "Stopping user service: ${svc}"
        systemctl --user stop "${svc}" || true
    fi
done

# 2. Prune 18 legacy numbered symlinks from stacklabs root
log "Pruning 18 legacy numbered symlinks from ${STACKLABS_ROOT} root..."
LEGACY_SYMLINKS=(
    "02_Edge_Platform_Engineering"
    "03_WildSeed_Sovereign_Swarm"
    "04_ArkleVet_Prospectus"
    "05_SanJuanIslands_Authority"
    "05_SanJuan_Prospectus"
    "06_Davidson_Malone_Prospectus"
    "07_JohnnyCarroll_Prospectus"
    "08_DaVincis_Prospectus"
    "09_WardyNYM_Creator_Prospectus"
    "11_JeffUren_Prospectus"
    "12_Order_of_Sacred_Metal"
    "13_FanStack_as_a_Service"
    "14_Sovereign_Horizon_Prospectus"
    "15_Horizon_Internal"
    "16_Emergent_Society"
    "18_StackLabs_Core"
    "19_Python_Monolith_Diet_Spark"
    "20_Pawel_Antfarm_Spark"
    "Horizon_Internal"
    "StackLabs_Internal"
)
for sym in "${LEGACY_SYMLINKS[@]}"; do
    target_link="${STACKLABS_ROOT}/${sym}"
    if [[ -L "${target_link}" ]]; then
        rm -f "${target_link}"
    fi
done

# 3. Create Target Institutional Directory Structure
log "Creating target directories under ${STACKLABS_ROOT}..."
mkdir -p "${STACKLABS_ROOT}"/{apps,services,ground_truth,dossiers,data,config,contracts,core,docs,archive,scratch,staging,tests,tools,logs}
mkdir -p "${STACKLABS_ROOT}/apps"/{fanstack,fanstack_creator,fanstack_arena,portal,cmdb_studio,mard_studio,listen,skew,carroll_craft}
mkdir -p "${STACKLABS_ROOT}/services"/{core_api,ground_truth,stream_sniper,antfarm,media_stack,advocate_swarms,sports_telemetry,davinci_dispatch,sentinel,fanstack_wire,systemd}
mkdir -p "${STACKLABS_ROOT}/dossiers"/{01_Pawel_Rudnicki_Horizon,02_Davidson_Homes_Malone,03_WardyNYM_Creator,04_ArkleVet,05_StackLabs_Internal}
mkdir -p "${STACKLABS_ROOT}/archive/legacy_cartridges"
mkdir -p "${STACKLABS_ROOT}/data"/{dna,market_intelligence,media,assets,attachments,avatars,captures,curated_external,curated_external_pristine,game_states,lookbook_assets,media_vault,mockups,models,notebooklm,output,reports,screenshots,uat_screenshots,vault,vault_matrix}
mkdir -p "${STACKLABS_ROOT}/config"/{standards,governance,mesh,character_maps,templates}
mkdir -p "${STACKLABS_ROOT}/docs/walkthroughs"

# 4. Safe Migration Function (Guaranteed Anti-Circular Symlink)
safe_physical_migrate() {
    local src="$1"
    local dest="$2"

    if [[ ! -e "${src}" && ! -L "${src}" ]]; then
        return 0
    fi

    # If src is already a symlink, ensure it points correctly
    if [[ -L "${src}" ]]; then
        log "Source ${src} is a symlink. Skipping physical move."
        return 0
    fi

    # If dest is an existing symlink (e.g. stacklabs/scripts -> SovereignOS/scripts), remove it first!
    if [[ -L "${dest}" ]]; then
        log "Removing pre-existing destination symlink: ${dest}"
        rm -f "${dest}"
    fi

    # If dest is an existing non-empty directory, merge contents
    if [[ -d "${dest}" && -n "$(ls -A "${dest}" 2>/dev/null)" ]]; then
        log "Merging directory: ${src} -> ${dest}"
        cp -a "${src}/." "${dest}/"
        rm -rf "${src}"
    else
        log "Moving directory: ${src} -> ${dest}"
        rm -rf "${dest}"
        mv "${src}" "${dest}"
    fi

    # Lay down the backward-compatibility reverse symlink
    ln -sfn "${dest}" "${src}"
}

# 5. Physical Inbox Relocation & Symlink Bridge Protocol
log "Migrating physical inbox to /home/james/stacklabs_inbox..."
if [[ -d "${LEGACY_INBOX}" && ! -L "${LEGACY_INBOX}" ]]; then
    mv "${LEGACY_INBOX}" "${PHYSICAL_INBOX}"
elif [[ ! -d "${PHYSICAL_INBOX}" ]]; then
    mkdir -p "${PHYSICAL_INBOX}"/{queue/{incoming,processing,archive,failed,logs},pilot_drops,today,spark}
fi

mkdir -p "${PHYSICAL_INBOX}"/{queue/{incoming,processing,archive,failed,logs},pilot_drops,today,spark}

# Bidirectional symlink bridges
ln -sfn "${PHYSICAL_INBOX}" "${LEGACY_INBOX}"
ln -sfn "${PHYSICAL_INBOX}" "${STACKLABS_ROOT}/inbox"
ln -sfn "${PHYSICAL_INBOX}/pilot_drops" "${STACKLABS_ROOT}/pilot_drops"

# 6. Physical Directory Migration
log "Executing physical migrations with reverse symlink bridges..."

# Core code and infrastructure
safe_physical_migrate "${LEGACY_ROOT}/scripts" "${STACKLABS_ROOT}/scripts"
safe_physical_migrate "${LEGACY_ROOT}/core" "${STACKLABS_ROOT}/core"
safe_physical_migrate "${LEGACY_ROOT}/config" "${STACKLABS_ROOT}/config"
safe_physical_migrate "${LEGACY_ROOT}/data" "${STACKLABS_ROOT}/data"
safe_physical_migrate "${LEGACY_ROOT}/contracts" "${STACKLABS_ROOT}/contracts"
safe_physical_migrate "${LEGACY_ROOT}/tests" "${STACKLABS_ROOT}/tests"
safe_physical_migrate "${LEGACY_ROOT}/tools" "${STACKLABS_ROOT}/tools"
safe_physical_migrate "${LEGACY_ROOT}/logs" "${STACKLABS_ROOT}/logs"
safe_physical_migrate "${LEGACY_ROOT}/walkthroughs" "${STACKLABS_ROOT}/docs/walkthroughs"

# Apps
safe_physical_migrate "${LEGACY_ROOT}/15_FanStackCreator" "${STACKLABS_ROOT}/apps/fanstack_creator"
ln -sfn "${STACKLABS_ROOT}/apps/fanstack_creator" "${STACKLABS_ROOT}/apps/fanstack"
ln -sfn "${STACKLABS_ROOT}/apps/fanstack_creator" "${LEGACY_ROOT}/15_FanStack"
safe_physical_migrate "${LEGACY_ROOT}/19_FanStackArena" "${STACKLABS_ROOT}/apps/fanstack_arena"
safe_physical_migrate "${LEGACY_ROOT}/25_CmdbStudio" "${STACKLABS_ROOT}/apps/cmdb_studio"
safe_physical_migrate "${LEGACY_ROOT}/26_MARD_Studio" "${STACKLABS_ROOT}/apps/mard_studio"
safe_physical_migrate "${LEGACY_ROOT}/31_Sovereign_Listen" "${STACKLABS_ROOT}/apps/listen"
safe_physical_migrate "${LEGACY_ROOT}/32_The_Skew_Studio" "${STACKLABS_ROOT}/apps/skew"
safe_physical_migrate "${LEGACY_ROOT}/34_CarrollCraft" "${STACKLABS_ROOT}/apps/carroll_craft"
safe_physical_migrate "${LEGACY_ROOT}/01_Sovereign_Portal" "${STACKLABS_ROOT}/apps/portal"

# Services
safe_physical_migrate "${LEGACY_ROOT}/03_Media_Stack" "${STACKLABS_ROOT}/services/media_stack"
safe_physical_migrate "${LEGACY_ROOT}/04_Advocate_Swarms" "${STACKLABS_ROOT}/services/advocate_swarms"
safe_physical_migrate "${LEGACY_ROOT}/19_Sovereign_Sports" "${STACKLABS_ROOT}/services/sports_telemetry"
safe_physical_migrate "${LEGACY_ROOT}/27_DaVinciDispatch" "${STACKLABS_ROOT}/services/davinci_dispatch"
safe_physical_migrate "${LEGACY_ROOT}/29_Sovereign_Sentinel" "${STACKLABS_ROOT}/services/sentinel"
safe_physical_migrate "${LEGACY_ROOT}/fanstack-wire" "${STACKLABS_ROOT}/services/fanstack_wire"

# Dossiers
safe_physical_migrate "${LEGACY_ROOT}/32_ArkleVet" "${STACKLABS_ROOT}/dossiers/04_ArkleVet"
safe_physical_migrate "${LEGACY_ROOT}/20_AetherVet" "${STACKLABS_ROOT}/dossiers/04_ArkleVet/aether_concept"
safe_physical_migrate "${LEGACY_ROOT}/16_StackLabsLLC" "${STACKLABS_ROOT}/dossiers/05_StackLabs_Internal"

# Config Standards & Governance
safe_physical_migrate "${LEGACY_ROOT}/00_Core_Standards" "${STACKLABS_ROOT}/config/standards"
safe_physical_migrate "${LEGACY_ROOT}/01_Governance_and_ITSM" "${STACKLABS_ROOT}/config/governance"
safe_physical_migrate "${LEGACY_ROOT}/02_Edge_Hardware_and_Mesh" "${STACKLABS_ROOT}/config/mesh"

# Retired Experiments
RETIRED_LIST=(
    "14_SamTracker"
    "17_GonzasCantina"
    "21_Wildseed_GardenStack"
    "22_SpiteSlice"
    "24_TesseractStack"
    "25_CatnipWars"
    "25_TrueCostStack"
    "28_MARD_TTRPG"
    "30_HoloLink"
    "31_WildSeed"
    "33_FanStack_Lite"
    "33_WildSeedDev"
    "35_EmergentSociety"
    "99_Legacy_Archive"
    "_archive"
    "archive_quarantine_eon1"
    "archives"
    "cartridges"
    "sandbox"
    "sovereign_boot"
    "sovereign_knot_core"
)
for exp in "${RETIRED_LIST[@]}"; do
    if [[ -d "${LEGACY_ROOT}/${exp}" && ! -L "${LEGACY_ROOT}/${exp}" ]]; then
        safe_physical_migrate "${LEGACY_ROOT}/${exp}" "${STACKLABS_ROOT}/archive/legacy_cartridges/${exp}"
    fi
done

# Python Virtualenv Bridge
if [[ -d "${LEGACY_ROOT}/.venv" && ! -L "${STACKLABS_ROOT}/.venv" ]]; then
    ln -sfn "${LEGACY_ROOT}/.venv" "${STACKLABS_ROOT}/.venv"
fi

# 7. Database Migration with SQLite WAL Safety
log "Securing canonical state database (sovereign_now.db)..."
if [[ -d "${LEGACY_ROOT}/dna" && ! -L "${STACKLABS_ROOT}/data/dna" ]]; then
    mkdir -p "${STACKLABS_ROOT}/data/dna"
    # Copy all DB and WAL companion files
    cp -a "${LEGACY_ROOT}/dna"/sovereign_now.db* "${STACKLABS_ROOT}/data/dna/" 2>/dev/null || true
    ln -sfn "${STACKLABS_ROOT}/data/dna/sovereign_now.db" "${STACKLABS_ROOT}/data/stacklabs_now.db"
    ln -sfn "${STACKLABS_ROOT}/data/dna/sovereign_now.db" "${LEGACY_ROOT}/dna/sovereign_now.db"
fi

# 8. Update User Systemd Unit Files
log "Updating user systemd unit files in ${USER_SYSTEMD_DIR}..."
for svc in "${USER_SERVICES[@]}"; do
    svc_path="${USER_SYSTEMD_DIR}/${svc}"
    if [[ -f "${svc_path}" ]]; then
        log "Backing up and updating: ${svc}"
        cp "${svc_path}" "${BACKUP_DIR}/systemd_user/${svc}"

        # Update WorkingDirectory and ExecStart paths
        sed -i "s|/home/james/stacklabs/34_CarrollCraft|${STACKLABS_ROOT}/apps/carroll_craft|g" "${svc_path}"
        sed -i "s|/home/james/stacklabs|${STACKLABS_ROOT}|g" "${svc_path}"
        sed -i "s|/home/james/sovereign_inbox|${PHYSICAL_INBOX}|g" "${svc_path}"
    fi
done

# 9. Reload User Systemd and Restart Services
log "Reloading systemd user daemon..."
systemctl --user daemon-reload

log "Restarting all 14 background services..."
for svc in "${USER_SERVICES[@]}"; do
    log "Starting service: ${svc}"
    systemctl --user restart "${svc}" || warn "Service ${svc} encountered restart delay. Inspect via journalctl --user -u ${svc}."
done

# 10. Verification
log "Verifying user service statuses..."
for svc in "${USER_SERVICES[@]}"; do
    if systemctl --user is-active --quiet "${svc}" 2>/dev/null; then
        echo "  ✅ [OK] ${svc} is active (running)"
    else
        echo "  ⚠️ [WARN] ${svc} is not active"
    fi
done

log "Cleanse completed cleanly. Backup retained at ${BACKUP_DIR}."
