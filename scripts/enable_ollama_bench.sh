#!/bin/bash
# =============================================================================
# SOVEREIGN OS — MODE SWITCHER: OLLAMA BENCHMARKING PROFILE
# Target Node: Clio Hub (clio - 192.168.1.183 / Port 11434)
# =============================================================================

set -euo pipefail

CYN='\033[0;36m'; GRN='\033[0;32m'; YLW='\033[1;33m'; RED='\033[0;31m'; BLD='\033[1m'; RST='\033[0m'

log_info() { echo -e "${CYN}[INFO]${RST}  $*"; }
log_ok()   { echo -e "${GRN}[OK]${RST}    $*"; }
log_warn() { echo -e "${YLW}[WARN]${RST}  $*"; }
log_err()  { echo -e "${RED}[ERROR]${RST} $*"; }

echo "=================================================="
echo -e " 🦙 ${BLD}SOVEREIGN OS: OLLAMA BENCHMARKING IGNITION${RST} 🦙"
echo "=================================================="

# 1. Graceful Hibernate FanStack Sports Telemetry & Relays
log_info "Executing surgical shutdown of FanStack daemons via stop_fanstack.sh..."
if [[ -f "/home/james/stacklabs/scripts/stop_fanstack.sh" ]]; then
    bash /home/james/stacklabs/scripts/stop_fanstack.sh || log_warn "FanStack shutdown completed with non-zero notice"
else
    log_warn "stop_fanstack.sh script not found. Proceeding with service check..."
fi

# 2. Engage Ollama Systemd Service
log_info "Starting Ollama inference engine on Port 11434..."
sudo systemctl start ollama.service

log_info "Waiting for Ollama API to bind on Port 11434..."
for i in {1..10}; do
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        log_ok "Ollama API successfully bound to http://localhost:11434"
        break
    fi
    sleep 1
done

# 3. Update System Mode Register in sovereign_now.db
log_info "Updating system mode register in knot_state.db..."
/home/james/stacklabs/.venv/bin/python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('/home/james/stacklabs/sovereign_knot_core/knot_state.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sys_variable (variable_key, status_value, last_verified_timestamp)
        VALUES ('SYSTEM_PROFILE', 'MODE_OLLAMA_BENCH', datetime('now'))
        ON CONFLICT(variable_key) DO UPDATE SET status_value = 'MODE_OLLAMA_BENCH', last_verified_timestamp = datetime('now')
    ''')
    conn.commit()
    conn.close()
    print('  ✓ SYSTEM_PROFILE updated to MODE_OLLAMA_BENCH')
except Exception as e:
    print('  ! Error updating SYSTEM_PROFILE:', e)
"

echo ""
echo "=================================================="
echo -e " ${GRN}${BLD}[✔] PROFILE ACTIVE: OLLAMA HEAVY BENCHMARKING (PORT 11434)${RST}"
echo "=================================================="
