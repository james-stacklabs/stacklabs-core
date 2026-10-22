#!/bin/bash
# =============================================================================
# SOVEREIGN OS — FANSTACK SURGICAL SHUTDOWN
# Version: 1.0 (Core-Preservation Architecture)
# Revised: 2026-06-24
#
# SDLC INVARIANTS:
#   • Core Preservation: Safely shuts down heavy sports telemetry, chatbots,
#     and streaming relays while keeping core system interfaces (Sovereign Core,
#     CMDB Server, SDLC Portal, Persona Manager) running.
#   • Surgical pkill: Targets exact script strings to prevent collateral damage.
# =============================================================================

set -euo pipefail

# --- COLORS (non-interactive safe) ------------------------------------------
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'
CYN='\033[0;36m'; BLD='\033[1m'; RST='\033[0m'

log_info()  { echo -e "${CYN}[INFO]${RST}  $*"; }
log_ok()    { echo -e "${GRN}[OK]${RST}    $*"; }
log_warn()  { echo -e "${YLW}[WARN]${RST}  $*"; }
log_err()   { echo -e "${RED}[ERROR]${RST} $*"; }

echo "=================================================="
echo -e " ⚾ ${BLD}SOVEREIGN OS: FIELD OF DREAMS HIBERNATION${RST} ⚾"
echo "=================================================="

# --- SURGICAL CLEANUP --------------------------------------------------------
_pkill_daemon() {
    local label="$1"
    local pattern="$2"
    # Use brackets to exclude the grep process itself
    local first=${pattern:0:1}
    local rest=${pattern:1}
    local regex_pattern="[${first}]${rest}"

    local pid
    pid=$(pgrep -f "${regex_pattern}" | head -1 2>/dev/null || true)

    if [[ -n "${pid}" ]]; then
        if kill -15 "${pid}" 2>/dev/null; then
            log_ok "SIGTERM sent to: ${label} (PID: ${pid})"
        else
            log_warn "Failed to send SIGTERM to: ${label} (PID: ${pid})"
        fi
    else
        log_info "Not running (clean state): ${label}"
    fi
}

log_info "Initiating surgical shutdown of FanStack telemetry and chatbot layers..."

# --- 1. ENTERPRISE CMDB MAINTENANCE TRANSITION (ENHC2026082203) ---
log_info "Setting FanStack CIs to Maintenance / Hibernation (operational_status = 2) in CMDB..."
sqlite3 /home/james/stacklabs/dna/sovereign_now.db "
UPDATE cmdb_ci 
SET operational_status = 2, sys_updated_on = CURRENT_TIMESTAMP 
WHERE name IN ('FanStackRelay', 'MARDChatEngine', 'FanStackPoller', 'SovereignSports', 'FanStackPortal');
" || true
log_ok "CMDB operational_status set to Maintenance (2). Mando Watchdog will suppress alerts and auto-restarts."

_pkill_daemon "mando_watchdog"            "mando_watchdog.py"
_pkill_daemon "fanstack_background_poller" "fanstack_background_poller.py"
_pkill_daemon "fanstack_chatbots"          "fanstack_chatbots.py"
_pkill_daemon "statcast_sentinel"          "statcast_sentinel.py"
_pkill_daemon "tmi_daemon"                 "tmi_daemon.py"
_pkill_daemon "fanstack_relay"             "fanstack_relay.py"
_pkill_daemon "fanstack_admin_api"         "fanstack_admin_api.py"
_pkill_daemon "stream_sniper_daemon"       "stream_sniper_daemon.py"
_pkill_daemon "dvr_controller_v2"          "dvr_controller_v2.py"
_pkill_daemon "gameday_continuous_sync"    "gameday_continuous_sync.py"
_pkill_daemon "cron_game_monitor"          "cron_game_monitor.py"
_pkill_daemon "pga_ingest_daemon"          "pga_ingest_daemon.py"

# Stop FanStack Vite server on port 3009 and 3010
if fuser 3009/tcp &>/dev/null; then
    log_warn "Releasing FanStack Vite dev server on Port 3009..."
    fuser -k 3009/tcp 2>/dev/null || true
    log_ok "Port 3009 released."
fi

if fuser 3010/tcp &>/dev/null; then
    log_warn "Releasing Sovereign Sports dev server on Port 3010..."
    fuser -k 3010/tcp 2>/dev/null || true
    log_ok "Port 3010 released."
fi

# --- GRACE PERIOD ------------------------------------------------------------
log_info "Waiting 2s for processes to exit gracefully..."
sleep 2

# --- FORCE KILL SURVIVORS ----------------------------------------------------
_force_pkill_daemon() {
    local label="$1"
    local pattern="$2"
    local first=${pattern:0:1}
    local rest=${pattern:1}
    local regex_pattern="[${first}]${rest}"

    local pid
    pid=$(pgrep -f "${regex_pattern}" | head -1 2>/dev/null || true)

    if [[ -n "${pid}" ]]; then
        if kill -9 "${pid}" 2>/dev/null; then
            log_warn "Force-killed lingering process: ${label} (PID: ${pid})"
        fi
    fi
}

_force_pkill_daemon "fanstack_background_poller" "fanstack_background_poller.py"
_force_pkill_daemon "fanstack_chatbots"          "fanstack_chatbots.py"
_force_pkill_daemon "statcast_sentinel"          "statcast_sentinel.py"
_force_pkill_daemon "tmi_daemon"                 "tmi_daemon.py"
_force_pkill_daemon "fanstack_relay"             "fanstack_relay.py"
_force_pkill_daemon "fanstack_admin_api"         "fanstack_admin_api.py"
_force_pkill_daemon "stream_sniper_daemon"       "stream_sniper_daemon.py"
_force_pkill_daemon "dvr_controller_v2"          "dvr_controller_v2.py"
_force_pkill_daemon "gameday_continuous_sync"    "gameday_continuous_sync.py"
_force_pkill_daemon "cron_game_monitor"          "cron_game_monitor.py"

# --- CORE STATUS ROLL CALL ---------------------------------------------------
echo ""
echo -e "${BLD}  CORE SYSTEM INFRASTRUCTURE STATUS${RST}"
echo -e "  ─────────────────────────────────────────────────"

_check_core() {
    local label="$1"
    local pattern="$2"
    local first=${pattern:0:1}
    local rest=${pattern:1}
    local regex_pattern="[${first}]${rest}"

    local pid
    pid=$(pgrep -f "${regex_pattern}" | head -1 2>/dev/null || true)

    if [[ -n "${pid}" ]]; then
        echo -e "  ${GRN}✓${RST} ${label} (PID: ${pid}) — ${GRN}RUNNING (PRESERVED)${RST}"
    else
        echo -e "  ${RED}✗${RST} ${label} — ${RED}NOT RUNNING${RST}"
    fi
}

_check_core "Sovereign Core API"      "sovereign_core_api.py"
_check_core "CMDB Server"             "cmdb_server.py"
_check_core "SDLC Ticketing Server"   "sdlc_portal_server.py"
_check_core "Persona Manager Server"  "persona_manager_server.py"
_check_core "Comet Relay"             "comet_relay.py"

echo ""
log_ok "=== FANSTACK HIBERNATION COMPLETE. CORE SERVICES PRESERVED. ==="
