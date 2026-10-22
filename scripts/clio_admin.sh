#!/usr/bin/env bash
# =============================================================================
# ⚔️ SOVEREIGN OS — REMOTE CONTROL PANEL & CLINICAL DIAGNOSTICS
# Designed for high-velocity SSH/Termux mobile administration.
# =============================================================================

set -u

# --- CONFIGURATION -----------------------------------------------------------
SOVEREIGN_HOME="/home/james/stacklabs"
LOG_DIR="${SOVEREIGN_HOME}/logs"
mkdir -p "$LOG_DIR"

# --- PALETTE (HSL-Inspired Sleek Modern Dark Mode) ---------------------------
RED='\033[38;2;239;68;68m'
GRN='\033[38;2;34;197;94m'
YLW='\033[38;2;234;179;8m'
BLU='\033[38;2;59;130;246m'
MAG='\033[38;2;168;85;247m'
CYN='\033[38;2;6;182;212m'
GRA='\033[38;2;156;163;175m'
BLD='\033[1m'
RST='\033[0m'

# --- HELPER FUNCTIONS --------------------------------------------------------
clear_screen() {
    printf "\033[H\033[2J"
}

draw_header() {
    echo -e "${BLD}${CYN}=================================================================${RST}"
    echo -e "  ${BLD}${MAG}⚔️  SOVEREIGN OS — REMOTE COCKPIT & CLINICAL DIAGNOSTICS${RST}"
    echo -e "  ${GRA}Optimized for Field Ops & Mobile Termux SSH${RST}"
    echo -e "${BLD}${CYN}=================================================================${RST}"
}

draw_footer() {
    echo -e "${BLD}${CYN}=================================================================${RST}"
}

wait_for_key() {
    echo -e "\n${GRA}Press [Enter] to return to the main cockpit...${RST}"
    read -r
}

# --- SERVICES DICT -----------------------------------------------------------
# Format: "Label|Port|ProcessPattern|StartScript|LogFile"
SERVICES=(
    "StackLabs Monolith|3000|16_StackLabsLLC|cd ${SOVEREIGN_HOME}/16_StackLabsLLC && nohup npm run dev -- --force --host 0.0.0.0 --port 3000 >> ${LOG_DIR}/vite_stacklabs.log 2>&1 &|vite_stacklabs.log"
    "Sovereign OS Portal|3016|01_Sovereign_Portal|cd ${SOVEREIGN_HOME}/01_Sovereign_Portal && nohup npm run dev -- --force --port 3016 >> ${LOG_DIR}/vite_portal.log 2>&1 &|vite_portal.log"
    "Sovereign Core API|8090|sovereign_core_api.py|cd ${SOVEREIGN_HOME} && nohup .venv/bin/python3 scripts/sovereign_core_api.py >> ${LOG_DIR}/sovereign_core_8090.log 2>&1 &|sovereign_core_8090.log"
    "SDLC Ticketing Server|8095|sdlc_portal_server.py|cd ${SOVEREIGN_HOME} && nohup .venv/bin/python3 scripts/sdlc_portal_server.py >> ${LOG_DIR}/sdlc_portal_server.log 2>&1 &|sdlc_portal_server.log"
    "Aether Vet Telemedicine|3015|20_AetherVet|cd ${SOVEREIGN_HOME}/20_AetherVet && nohup npm run dev -- --host 0.0.0.0 --port 3015 >> ${LOG_DIR}/aether_vet.log 2>&1 &|aether_vet.log"
    "Sovereign Media|3008|02_Sovereign_Media|cd ${SOVEREIGN_HOME}/02_Sovereign_Media && nohup npm run dev -- --host 0.0.0.0 --port 3008 >> ${LOG_DIR}/vite_cinema.log 2>&1 &|vite_cinema.log"
    "SamTracker Frontend|3024|14_SamTracker|cd ${SOVEREIGN_HOME}/14_SamTracker && nohup npm run dev -- --force --port 3024 >> ${LOG_DIR}/vite_sam.log 2>&1 &|vite_sam.log"
    "SamTracker Backend|8083|sam_tracker_server.py|cd ${SOVEREIGN_HOME} && nohup .venv/bin/python3 scripts/sam_tracker_server.py >> ${LOG_DIR}/sam_tracker.log 2>&1 &|sam_tracker.log"
    "Storybook Station|3017|23_EileenStack|cd ${SOVEREIGN_HOME}/23_EileenStack && nohup npm run dev -- --force --port 3017 >> ${LOG_DIR}/vite_garden.log 2>&1 &|vite_garden.log"
    "BistroPortal|3006|16_BistroPortal|cd ${SOVEREIGN_HOME}/16_BistroPortal && nohup npm run dev -- --force --port 3006 >> ${LOG_DIR}/vite_bistro.log 2>&1 &|vite_bistro.log"
    "Theater Media Server|8085|theater_media_server.py|cd ${SOVEREIGN_HOME} && nohup python3 scripts/theater_media_server.py >> ${LOG_DIR}/theater_media_8085.log 2>&1 &|theater_media_8085.log"
    "JIT Mobile Approval Gateway|3027|approval_gateway/main.py|sudo systemctl restart jit_approval_gateway.service 2>/dev/null || (cd ${SOVEREIGN_HOME}/services/approval_gateway && nohup ${SOVEREIGN_HOME}/.venv/bin/python3 main.py >> ${LOG_DIR}/jit_approval.log 2>&1 &)|jit_approval.log"
    "Sovereign CMDB Studio|3025|25_CmdbStudio|sudo systemctl restart cmdb_studio.service 2>/dev/null || (cd ${SOVEREIGN_HOME}/25_CmdbStudio && nohup npm run dev -- --host 127.0.0.1 --port 3025 >> ${LOG_DIR}/vite_cmdb_studio.log 2>&1 &)|vite_cmdb_studio.log"
    "GreenStack Botanical Ops|3021|21_Wildseed_GardenStack|cd ${SOVEREIGN_HOME}/21_Wildseed_GardenStack && nohup npm run dev -- --host 0.0.0.0 --port 3021 >> ${LOG_DIR}/vite_greenstack.log 2>&1 &|vite_greenstack.log"
)

# =============================================================================
# OPTION 1: CLINICAL STATUS & METRICS
# =============================================================================
show_status() {
    clear_screen
    draw_header
    echo -e "  ${BLD}${YLW}📊 ACTIVE PORT & SERVICE MESH${RST}"
    echo -e "  -------------------------------------------------"
    
    # Header format
    printf "  %-26s %-6s %-10s %-8s\n" "Service Name" "Port" "Status" "PID"
    echo -e "  -------------------------------------------------"

    for svc in "${SERVICES[@]}"; do
        IFS='|' read -r label port pattern start cmd log <<< "$svc"
        
        # Check if port is listening
        if ss -tlnp 2>/dev/null | grep -q ":${port}"; then
            port_status="${GRN}BOUND${RST}"
        else
            port_status="${RED}UNBOUND${RST}"
        fi

        # Find PID
        pid=$(pgrep -f "${pattern}" | head -n 1)
        if [[ -n "$pid" ]]; then
            proc_status="${GRN}ONLINE${RST}"
            pid_str="${pid}"
        else
            proc_status="${RED}OFFLINE${RST}"
            pid_str="--"
        fi

        # Render row
        if [[ "$port_status" == *BOUND* ]] || [[ "$proc_status" == *ONLINE* ]]; then
            status_indicator="${GRN}●${RST} ${GRN}RUNNING${RST}"
        else
            status_indicator="${RED}○${RST} ${GRA}STOPPED${RST}"
        fi

        printf "  %-26s %-6s %-18s %-8s\n" "${label}" "${port}" "${status_indicator}" "${pid_str}"
    done

    echo -e "\n  ${BLD}${YLW}🌐 TAILSCALE SERVE STATUS (MESH-ONLY)${RST}"
    echo -e "  -------------------------------------------------"
    if command -v tailscale &>/dev/null; then
        tailscale serve status 2>&1 | sed 's/^/  /'
    else
        echo -e "  ${RED}✗ Tailscale binary not found in PATH.${RST}"
    fi

    echo -e "\n  ${BLD}${YLW}🖥️  CLIO HARDWARE TELEMETRY${RST}"
    echo -e "  -------------------------------------------------"
    load=$(uptime | awk -F'load average:' '{print $2}' | sed 's/^ //')
    mem=$(free -m | awk '/Mem:/ {printf "Total: %dMB, Used: %dMB (%.1f%%)", $2, $3, ($3/$2)*100}')
    echo -e "  ${BLD}CPU Load average:${RST} $load"
    echo -e "  ${BLD}RAM Utilization:${RST} $mem"
    
    # Check if Watchdog daemon is running
    wd_pid=$(pgrep -f "mando_watchdog.py")
    if [[ -n "$wd_pid" ]]; then
        echo -e "  ${BLD}Mando Watchdog:${RST} ${GRN}● RUNNING (PID: $wd_pid)${RST}"
    else
        echo -e "  ${BLD}Mando Watchdog:${RST} ${RED}○ OFFLINE${RST}"
    fi

    draw_footer
    wait_for_key
}

# =============================================================================
# OPTION 2: SURGICAL PORT REBOOTS
# =============================================================================
surgical_reboots() {
    while true; do
        clear_screen
        draw_header
        echo -e "  ${BLD}${YLW}⚡ SURGICAL SERVICE ENGINE${RST}"
        echo -e "  Pick a service to restart natively on Clio:\n"

        local i=1
        for svc in "${SERVICES[@]}"; do
            IFS='|' read -r label port pattern start cmd log <<< "$svc"
            
            # Find PID
            pid=$(pgrep -f "${pattern}" | head -n 1)
            if [[ -n "$pid" ]]; then
                status_indicator="[${GRN}ONLINE${RST}]"
            else
                status_indicator="[${RED}OFFLINE${RST}]"
            fi
            
            printf "  %2d) %-28s %s (Port %s)\n" "$i" "${label}" "$status_indicator" "${port}"
            i=$((i + 1))
        done
        echo -e "  all) Restart ENTIRE stack surgical sequence"
        echo -e "    q) Return to cockpit"
        echo -e "  -------------------------------------------------"
        echo -n "  Enter option: "
        read -r choice

        if [[ "$choice" == "q" ]]; then
            break
        elif [[ "$choice" == "all" ]]; then
            echo -e "\n  ${BLD}${YLW}🚨 Initiating Surgical Stack Restart Sequence...${RST}"
            for svc in "${SERVICES[@]}"; do
                IFS='|' read -r label port pattern start cmd log <<< "$svc"
                echo -e "  [+] Restarting $label (killing listeners on $port)..."
                # Kill existing listener ports
                pids=$(lsof -t -i:"$port" 2>/dev/null)
                if [[ -n "$pids" ]]; then
                    kill -9 $pids 2>/dev/null || true
                fi
                # Kill by process pattern
                pkill -9 -f "${pattern}" 2>/dev/null || true
                
                # Start in background
                eval "$start"
                sleep 0.5
            done
            echo -e "  ${GRN}✔ Full stack rebooted successfully!${RST}"
            sleep 2
            break
        elif [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#SERVICES[@]}" ]; then
            idx=$((choice - 1))
            svc="${SERVICES[$idx]}"
            IFS='|' read -r label port pattern start cmd log <<< "$svc"
            
            echo -e "\n  ${BLD}${YLW}♻️  Rebooting $label...${RST}"
            
            # Kill current listeners
            echo -e "  [+] Freeing Port $port..."
            pids=$(lsof -t -i:"$port" 2>/dev/null)
            if [[ -n "$pids" ]]; then
                kill -9 $pids 2>/dev/null || true
            fi
            
            # Process kill-pattern
            pkill -9 -f "${pattern}" 2>/dev/null || true
            sleep 1

            # Launch command
            echo -e "  [+] Executing start sequence..."
            eval "$start"
            sleep 2

            # Confirm startup
            new_pid=$(pgrep -f "${pattern}" | head -n 1)
            if [[ -n "$new_pid" ]]; then
                echo -e "  ${GRN}✔ $label is ONLINE on Port $port (PID: $new_pid)${RST}"
            else
                echo -e "  ${RED}⚠ Failed to startup. Check $log for details.${RST}"
            fi
            sleep 2
        else
            echo -e "  ${RED}Invalid option, try again.${RST}"
            sleep 1
        fi
    done
}

# =============================================================================
# OPTION 3: TAILSCALE SERVE DIAGNOSTICS
# =============================================================================
tailscale_serve_diagnostics() {
    clear_screen
    draw_header
    echo -e "  ${BLD}${YLW}🌐 TAILSCALE SERVE DIAGNOSTICS (MESH-ONLY)${RST}"
    echo -e "  -------------------------------------------------"
    echo -e "  This diagnostics view dumps active Tailscale serve configurations."
    echo -e "  Funnel is decommissioned per KI-048 (Tailscale Mesh-Only Law)."
    echo -e "  -------------------------------------------------\n"
    
    echo -e "  Active Tailscale Serve Status:"
    echo -e "  -------------------------------------------------"
    if command -v tailscale &>/dev/null; then
        sudo tailscale serve status 2>&1 | sed 's/^/  /'
    else
        echo -e "  ${RED}✗ Tailscale binary not found.${RST}"
    fi
    
    draw_footer
    wait_for_key
}

# =============================================================================
# OPTION 4: CLINICAL AUDIT LOGGER
# =============================================================================
view_audit_logs() {
    while true; do
        clear_screen
        draw_header
        echo -e "  ${BLD}${YLW}🪵  CLIO CLINICAL AUDIT LOGGER${RST}"
        echo -e "  Select a service log file to tail (last 50 lines):\n"

        local i=1
        for svc in "${SERVICES[@]}"; do
            IFS='|' read -r label port pattern start cmd log <<< "$svc"
            printf "  %2d) %-28s (%s)\n" "$i" "${label}" "${log}"
            i=$((i + 1))
        done
        printf "  %2d) Mando Watchdog Log         (mando_watchdog.log)\n" "$i"
        echo -e "    q) Return to cockpit"
        echo -e "  -------------------------------------------------"
        echo -n "  Enter option: "
        read -r choice

        if [[ "$choice" == "q" ]]; then
            break
        elif [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le $(( ${#SERVICES[@]} + 1 )) ]; then
            local file_to_tail=""
            if [ "$choice" -eq $(( ${#SERVICES[@]} + 1 )) ]; then
                # Find where watchdog logs are written
                # mando_watchdog.py runs under nohup, let's look for nohup.out or check running service logs
                file_to_tail="${SOVEREIGN_HOME}/logs/mando_watchdog.log"
                if [[ ! -f "$file_to_tail" ]]; then
                    # Fallback to current directory nohup
                    file_to_tail="${SOVEREIGN_HOME}/nohup.out"
                fi
            else
                idx=$((choice - 1))
                svc="${SERVICES[$idx]}"
                IFS='|' read -r label port pattern start cmd log <<< "$svc"
                file_to_tail="${LOG_DIR}/${log}"
            fi

            if [[ -f "$file_to_tail" ]]; then
                clear_screen
                echo -e "${BLD}${CYN}=================================================================${RST}"
                echo -e "  ${BLD}${MAG}🪵  LOG TAIL: ${file_to_tail}${RST}"
                echo -e "  ${GRA}Press [Ctrl+C] to stop tailing logs.${RST}"
                echo -e "${BLD}${CYN}=================================================================${RST}"
                tail -n 50 -f "$file_to_tail"
            else
                echo -e "  ${RED}⚠ Log file not created yet: ${file_to_tail}${RST}"
                sleep 2
            fi
        else
            echo -e "  ${RED}Invalid option, try again.${RST}"
            sleep 1
        fi
    done
}

# =============================================================================
# OPTION 5: WATCHDOG CONTROL PANEL
# =============================================================================
watchdog_control() {
    while true; do
        clear_screen
        draw_header
        echo -e "  ${BLD}${YLW}🐕 MANDO WATCHDOG CONTROL DECK${RST}"
        echo -e "  -------------------------------------------------"
        
        wd_pid=$(pgrep -f "mando_watchdog.py")
        if [[ -n "$wd_pid" ]]; then
            echo -e "  Watchdog Status: ${GRN}● ONLINE (PID: $wd_pid)${RST}"
            echo -e "  1) Stop Watchdog Daemon"
        else
            echo -e "  Watchdog Status: ${RED}○ OFFLINE${RST}"
            echo -e "  1) Start Watchdog Daemon"
        fi
        echo -e "  2) Tail Watchdog Heartbeat Output"
        echo -e "  q) Return to cockpit"
        echo -e "  -------------------------------------------------"
        echo -n "  Enter choice: "
        read -r choice

        if [[ "$choice" == "q" ]]; then
            break
        elif [[ "$choice" == "1" ]]; then
            if [[ -n "$wd_pid" ]]; then
                echo -e "\n  [-] Killing Watchdog Daemon (PID $wd_pid)..."
                kill "$wd_pid"
                sleep 1.5
            else
                echo -e "\n  [+] Starting Mando Watchdog Daemon..."
                nohup python3 "${SOVEREIGN_HOME}/scripts/mando_watchdog.py" >> "${LOG_DIR}/mando_watchdog.log" 2>&1 &
                sleep 1.5
            fi
        elif [[ "$choice" == "2" ]]; then
            wd_log="${LOG_DIR}/mando_watchdog.log"
            if [[ ! -f "$wd_log" ]]; then
                wd_log="${SOVEREIGN_HOME}/nohup.out"
            fi
            if [[ -f "$wd_log" ]]; then
                clear_screen
                echo -e "${BLD}${CYN}=================================================================${RST}"
                echo -e "  ${BLD}${MAG}🐕 WATCHDOG HEARTBEAT: ${wd_log}${RST}"
                echo -e "  ${GRA}Press [Ctrl+C] to stop tailing logs.${RST}"
                echo -e "${BLD}${CYN}=================================================================${RST}"
                tail -n 50 -f "$wd_log"
            else
                echo -e "  ${RED}⚠ No heartbeat log found yet.${RST}"
                sleep 2
            fi
        fi
    done
}

# =============================================================================
# COCKPIT CORE LOOP
# =============================================================================
main_menu() {
    while true; do
        clear_screen
        draw_header
        echo -e "  Please choose an administrative quadrant:\n"
        echo -e "  ${BLD}${CYN}1)${RST} ${BLD}Clinical Mesh Status${RST}        - Quick diagnostic overview of ports & PIDs"
        echo -e "  ${BLD}${CYN}2)${RST} ${BLD}Surgical Service Reboot${RST}     - Safely reboot single or all services"
        echo -e "  ${BLD}${CYN}3)${RST} ${BLD}Tailscale Serve Status${RST}      - View mesh-only routing configurations"
        echo -e "  ${BLD}${CYN}4)${RST} ${BLD}Clinical Audit Logger${RST}       - Tail logs for active services"
        echo -e "  ${BLD}${CYN}5)${RST} ${BLD}Watchdog Control Deck${RST}       - Start, stop, or view the watchdog"
        echo -e "  ${BLD}${CYN}q)${RST} ${BLD}Exit Control Cockpit${RST}       - Exit cleanly back to Bash"
        echo -e "\n  -------------------------------------------------"
        echo -n "  Enter choice: "
        read -r option

        case "$option" in
            1) show_status ;;
            2) surgical_reboots ;;
            3) tailscale_serve_diagnostics ;;
            4) view_audit_logs ;;
            5) watchdog_control ;;
            q) 
                clear_screen
                echo -e "\n  ${GRN}✔ Exiting Cockpit safely. Clear skies, Pilot!${RST}\n"
                break 
                ;;
            *)
                echo -e "  ${RED}Quadrant unknown. Please check coordinates.${RST}"
                sleep 1
                ;;
        esac
    done
}

main_menu
