#!/bin/bash
# =============================================================================
# SOVEREIGN OS — MODE SWITCHER: FANSTACK LIVE SPORTS PROFILE
# Target Node: Clio Hub (clio - 192.168.1.183 / Port 8008 / Port 3009)
# =============================================================================

set -euo pipefail

CYN='\033[0;36m'; GRN='\033[0;32m'; YLW='\033[1;33m'; RED='\033[0;31m'; BLD='\033[1m'; RST='\033[0m'

log_info() { echo -e "${CYN}[INFO]${RST}  $*"; }
log_ok()   { echo -e "${GRN}[OK]${RST}    $*"; }
log_warn() { echo -e "${YLW}[WARN]${RST}  $*"; }
log_err()  { echo -e "${RED}[ERROR]${RST} $*"; }

echo "=================================================="
echo -e " ⚾ ${BLD}SOVEREIGN OS: FANSTACK LIVE SPORTS IGNITION${RST} ⚾"
echo "=================================================="

# 1. Unload Heavy Ollama Inference
log_info "Stopping local Ollama inference service to free VRAM/RAM..."
sudo systemctl stop ollama.service || log_warn "Ollama service was not running"
log_ok "Ollama inference service halted."

# 2. Reignite FanStack Broadcast Mesh
log_info "Reigniting FanStack relay mesh & advocate daemons via start_fanstack.sh..."
if [[ -f "/home/james/stacklabs/scripts/start_fanstack.sh" ]]; then
    bash /home/james/stacklabs/scripts/start_fanstack.sh || log_warn "start_fanstack.sh output warning"
else
    log_err "start_fanstack.sh not found!"
    exit 1
fi

# 3. Update System Mode Register in sovereign_now.db
log_info "Updating system mode register in knot_state.db..."
/home/james/stacklabs/.venv/bin/python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('/home/james/stacklabs/sovereign_knot_core/knot_state.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sys_variable (variable_key, status_value, last_verified_timestamp)
        VALUES ('SYSTEM_PROFILE', 'MODE_FANSTACK_ACTIVE', datetime('now'))
        ON CONFLICT(variable_key) DO UPDATE SET status_value = 'MODE_FANSTACK_ACTIVE', last_verified_timestamp = datetime('now')
    ''')
    conn.commit()
    conn.close()
    print('  ✓ SYSTEM_PROFILE updated to MODE_FANSTACK_ACTIVE')
except Exception as e:
    print('  ! Error updating SYSTEM_PROFILE:', e)
"

echo ""
echo "=================================================="
echo -e " ${GRN}${BLD}[✔] PROFILE ACTIVE: FANSTACK LIVE SPORTS (PORT 8008 / PORT 3009)${RST}"
echo "=================================================="
