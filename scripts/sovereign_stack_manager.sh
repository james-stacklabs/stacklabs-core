#!/bin/bash
# =============================================================================
# SOVEREIGN OS — INTERACTIVE STACK MANAGER
# Script: /home/james/stacklabs/scripts/sovereign_stack_manager.sh
# Work Order: WO-2026-OLLAMA-CHAT-ARENA-004
# =============================================================================

set -e

SOVEREIGN_HOME="/home/james/stacklabs"
LOG_DIR="${SOVEREIGN_HOME}/logs"
mkdir -p "${LOG_DIR}"

# --- COLORS ------------------------------------------------------------------
RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
CYN='\033[0;36m'
BLD='\033[1m'
RST='\033[0m'

# --- SERVICE MAPPING CONFIGURATION -------------------------------------------
# Format: service_name | port | directory | logfile | launch_cmd
get_service_info() {
    local name="$1"
    case "${name}" in
        portal)
            echo "3016|${SOVEREIGN_HOME}/01_Sovereign_Portal|vite_portal.log|npm run dev -- --host 0.0.0.0 --port 3016"
            ;;
        fanstack|creator)
            echo "3009|${SOVEREIGN_HOME}/15_FanStackCreator|vite_fanstack.log|npm run dev -- --host 0.0.0.0 --port 3009"
            ;;
        arena|sports)
            echo "3010|${SOVEREIGN_HOME}/19_FanStackArena|vite_sports.log|npm run dev -- --host 0.0.0.0 --port 3010"
            ;;
        stacklabs)
            echo "3000|${SOVEREIGN_HOME}/16_StackLabsLLC|vite_stacklabs.log|npm run dev -- --host 0.0.0.0 --port 3000"
            ;;
        cinema)
            echo "3008|${SOVEREIGN_HOME}/02_Sovereign_Media|vite_cinema.log|npm run dev -- --host 0.0.0.0 --port 3008"
            ;;
        samtracker)
            echo "3004|${SOVEREIGN_HOME}/14_SamTracker|vite_sam.log|npm run dev -- --host 0.0.0.0 --port 3004"
            ;;
        ollama)
            echo "11434|${SOVEREIGN_HOME}|ollama.log|ollama serve"
            ;;
        jit_approval)
            echo "3027|${SOVEREIGN_HOME}/services/approval_gateway|jit_approval.log|${SOVEREIGN_HOME}/.venv/bin/python3 main.py"
            ;;
        cmdb_studio)
            echo "3025|${SOVEREIGN_HOME}/25_CmdbStudio|vite_cmdb_studio.log|npm run dev -- --host 127.0.0.1 --port 3025"
            ;;
        listen)
            echo "3040|${SOVEREIGN_HOME}/31_Sovereign_Listen|vite_listen.log|npm run dev -- --host 0.0.0.0 --port 3040"
            ;;
        *)
            echo ""
            ;;
    esac
}

ALL_SERVICES="portal fanstack arena stacklabs cinema samtracker ollama jit_approval cmdb_studio listen"

log_info()  { echo -e "${CYN}[INFO]${RST}  $*"; }
log_ok()    { echo -e "${GRN}[OK]${RST}    $*"; }
log_warn()  { echo -e "${YLW}[WARN]${RST}  $*"; }
log_err()   { echo -e "${RED}[ERROR]${RST} $*"; }

# --- HELPER FUNCTIONS --------------------------------------------------------
is_port_active() {
    local port="$1"
    ss -tlnp 2>/dev/null | grep -q ":${port} " || ss -tlnp 2>/dev/null | grep -q ":${port}\b"
}

get_port_pid() {
    local port="$1"
    local pid
    pid=$(fuser "${port}/tcp" 2>/dev/null | tr -d ' ' || true)
    if [[ -z "${pid}" ]]; then
        pid=$(ss -tlnp 2>/dev/null | grep ":${port}\b" | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1 || true)
    fi
    echo "${pid}"
}

status_service() {
    local name="$1"
    local info
    info=$(get_service_info "${name}")
    if [[ -z "${info}" ]]; then
        log_err "Unknown service: ${name}"
        return 1
    fi

    IFS='|' read -r port dir logfile launch_cmd <<< "${info}"
    local pid
    pid=$(get_port_pid "${port}")

    if is_port_active "${port}"; then
        echo -e "  ${GRN}● ACTIVE${RST}   ${BLD}${name}${RST} (Port ${port}, PID: ${pid:-unknown})"
    else
        echo -e "  ${RED}○ STOPPED${RST}  ${BLD}${name}${RST} (Port ${port})"
    fi
}

start_service() {
    local name="$1"
    local info
    info=$(get_service_info "${name}")
    if [[ -z "${info}" ]]; then
        log_err "Unknown service: ${name}"
        return 1
    fi

    IFS='|' read -r port dir logfile launch_cmd <<< "${info}"

    if is_port_active "${port}"; then
        log_warn "Service '${name}' is already running on Port ${port}."
        return 0
    fi

    log_info "Starting ${name} on Port ${port}..."

    if [[ "${name}" == "ollama" ]]; then
        nohup ollama serve >> "${LOG_DIR}/${logfile}" 2>&1 &
        disown $!
    else
        if [[ ! -d "${dir}" ]]; then
            log_err "Directory ${dir} not found for ${name}!"
            return 1
        fi
        cd "${dir}"
        nohup npm run dev -- --host 0.0.0.0 --port "${port}" --strictPort >> "${LOG_DIR}/${logfile}" 2>&1 &
        disown $!
        cd "${SOVEREIGN_HOME}"
    fi

    sleep 2
    if is_port_active "${port}"; then
        log_ok "Service '${name}' started successfully on Port ${port}."
    else
        log_warn "Service '${name}' spawned process, waiting for port binding..."
    fi
}

stop_service() {
    local name="$1"
    local info
    info=$(get_service_info "${name}")
    if [[ -z "${info}" ]]; then
        log_err "Unknown service: ${name}"
        return 1
    fi

    IFS='|' read -r port dir logfile launch_cmd <<< "${info}"

    if ! is_port_active "${port}"; then
        log_info "Service '${name}' is not running on Port ${port}."
        return 0
    fi

    log_info "Stopping ${name} on Port ${port}..."
    if fuser -k "${port}/tcp" 2>/dev/null; then
        log_ok "Released Port ${port} for ${name}."
    else
        pkill -f "port ${port}" 2>/dev/null || pkill -f "${dir}" 2>/dev/null || true
    fi

    sleep 1
    if is_port_active "${port}"; then
        fuser -k -9 "${port}/tcp" 2>/dev/null || true
    fi
    log_ok "Service '${name}' stopped."
}

restart_service() {
    local name="$1"
    stop_service "${name}"
    sleep 1
    start_service "${name}"
}

parse_services() {
    local arg="$1"
    if [[ "${arg}" == "all" ]]; then
        echo "${ALL_SERVICES}"
    else
        echo "${arg}" | tr ',' ' '
    fi
}

show_status_all() {
    echo -e "\n${BLD}${CYN}═══ SOVEREIGN OS STACK STATUS ═══${RST}"
    for svc in ${ALL_SERVICES}; do
        status_service "${svc}"
    done
    echo ""
}

show_help() {
    echo -e "${BLD}SOVEREIGN OS STACK MANAGER${RST}"
    echo -e "Usage: $0 [OPTION] [SERVICES]\n"
    echo -e "Options:"
    echo -e "  --start <services|all>    Start specified service(s) (comma-separated or 'all')"
    echo -e "  --stop <services|all>     Stop specified service(s)"
    echo -e "  --restart <services|all>  Restart specified service(s)"
    echo -e "  --status                  Display status of all managed services"
    echo -e "  --help                    Display this help message\n"
    echo -e "Managed Services:"
    echo -e "  portal, fanstack, stacklabs, cinema, samtracker, ollama\n"
    echo -e "Interactive Mode:"
    echo -e "  Run without options for interactive menu: $0"
}

interactive_menu() {
    while true; do
        show_status_all
        echo -e "${BLD}Select an action:${RST}"
        echo -e "  ${CYN}1)${RST} Start Service(s)"
        echo -e "  ${CYN}2)${RST} Stop Service(s)"
        echo -e "  ${CYN}3)${RST} Restart Service(s)"
        echo -e "  ${CYN}4)${RST} Refresh Status"
        echo -e "  ${CYN}5)${RST} Exit"
        echo -n "Option [1-5]: "
        read -r choice
        case "${choice}" in
            1)
                echo -n "Enter service name(s) to start (or 'all'): "
                read -r target
                for s in $(parse_services "${target}"); do
                    start_service "${s}"
                done
                ;;
            2)
                echo -n "Enter service name(s) to stop (or 'all'): "
                read -r target
                for s in $(parse_services "${target}"); do
                    stop_service "${s}"
                done
                ;;
            3)
                echo -n "Enter service name(s) to restart (or 'all'): "
                read -r target
                for s in $(parse_services "${target}"); do
                    restart_service "${s}"
                done
                ;;
            4)
                continue
                ;;
            5|q|quit|exit)
                log_info "Exiting Stack Manager."
                break
                ;;
            *)
                log_warn "Invalid option."
                ;;
        esac
    done
}

# --- MAIN EXECUTION ROUTER ---------------------------------------------------
if [[ $# -eq 0 ]]; then
    interactive_menu
    exit 0
fi

case "$1" in
    --status)
        show_status_all
        ;;
    --start)
        if [[ -z "${2:-}" ]]; then
            log_err "Missing service parameter for --start. Use 'all' or comma-separated list."
            exit 1
        fi
        for s in $(parse_services "$2"); do
            start_service "${s}"
        done
        ;;
    --stop)
        if [[ -z "${2:-}" ]]; then
            log_err "Missing service parameter for --stop. Use 'all' or comma-separated list."
            exit 1
        fi
        for s in $(parse_services "$2"); do
            stop_service "${s}"
        done
        ;;
    --restart)
        if [[ -z "${2:-}" ]]; then
            log_err "Missing service parameter for --restart. Use 'all' or comma-separated list."
            exit 1
        fi
        for s in $(parse_services "$2"); do
            restart_service "${s}"
        done
        ;;
    --help|-h)
        show_help
        ;;
    *)
        log_err "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
