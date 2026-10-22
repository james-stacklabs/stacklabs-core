#!/bin/bash
# Enforce strict headless sandbox variables
export DISPLAY=""
export PLAYWRIGHT_HEADLESS=true

echo "=================================================="
echo " ⚾ SOVEREIGN OS: FIELD OF DREAMS IGNITION ⚾"
echo "=================================================="

# --- 0. ENTERPRISE CMDB OPERATIONAL STATUS ACTIVATION (ENHC2026082203) ---
echo "[+] Setting FanStack CIs to Operational (operational_status = 1) in CMDB..."
sqlite3 /home/james/stacklabs/dna/sovereign_now.db "
UPDATE cmdb_ci 
SET operational_status = 1, sys_updated_on = CURRENT_TIMESTAMP 
WHERE name IN ('FanStackRelay', 'MARDChatEngine', 'FanStackPoller', 'SovereignSports', 'FanStackPortal');
" || true

# 1. Start Sovereign Core API
echo "[+] Waking Sovereign Core OS Interface (Port 8090)..."
nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/sovereign_core_api.py > /tmp/sovereign_core.log 2>&1 &
sleep 2

# 2. Start the WebSocket Relay
echo "[+] Igniting Mesh Relay (Port 8008)..."
nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/fanstack_relay.py > /tmp/relay.log 2>&1 &
sleep 2

# # 2.1 Start The Skew Relay (Decommissioned)
# echo "[+] Igniting The Skew Relay (Port 8009)..."
# nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/the_skew_relay.py > /tmp/skew_relay.log 2>&1 &
# sleep 2

# 3. Start the Agent Personas
echo "[+] Waking LLM Personas (Dot, Barf, Phanatic...)"
nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/fanstack_chatbots.py > /tmp/chatbots.log 2>&1 &
sleep 2

# # 3.1 Start The Skew Chatbots (Decommissioned)
# echo "[+] Waking The Skew Chatbots..."
# nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/the_skew_chatbots.py > /tmp/skew_chatbots.log 2>&1 &
# sleep 2

# 3. Start the CMDB Server for [INTEL_REQ]
echo "[+] Starting CMDB API (Port 8082)..."
nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/cmdb_server.py > /tmp/cmdb.log 2>&1 &
sleep 2

# 4. Start Savant Sentinel
echo "[+] Engaging Local Telemetry Refinery..."
nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/statcast_sentinel.py > /tmp/statcast.log 2>&1 &
sleep 2

# 5. Start Hailo/LLaVA Dashboard
echo "[+] Arming Vanguard Airgap Pipeline (Port 8086)..."
nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/hailo_dashboard.py > /tmp/hailo.log 2>&1 &

# 6. Start Persona Manager
echo "[+] Starting Persona Registry..."
nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/persona_manager_server.py > /tmp/persona_manager.log 2>&1 &

# 7. Start Agent Courier Backend
echo "[+] Starting Agent Courier Payload Engine..."
nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/fanstack_admin/fanstack_admin_api.py > /tmp/admin_api.log 2>&1 &

# 8. Start Sovereign Stream Relay
echo "[+] Starting Sovereign Stream Relay (Port 8097)..."
nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/sovereign_stream_relay.py > /home/james/stacklabs/logs/sovereign_stream_relay.log 2>&1 &

echo ""
echo "=================================================="
echo " [✔] MESH SECURED. THE ORACLE IS LISTENING."
echo "=================================================="
echo " LOAD YOUR UI NODES (via Vite SPA Port 3009):"
echo " 1. Operations Desk (Kanban) -> https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=kanban"
echo " 2. Savant Hub (Query)       -> https://clio.taila01894.ts.net:3009/?domain=MLB&room=savant_query"
echo " 3. Broadcast (Game)         -> https://clio.taila01894.ts.net:3009/?domain=MLB&room=scruffys"
echo " 4. Tricorder (Remote)       -> https://clio.taila01894.ts.net:3009/?view=remote"
echo "=================================================="
