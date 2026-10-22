#!/bin/bash
# =============================================================================
# SOVEREIGN OS — CINEMA & AUTH SURGICAL RESTORATION SCRIPT
# Version: 1.0
# Purpose: Surgically restarts Sovereign OS Portal (3016), Core API / Auth (8090),
#          Sovereign Cinema (3008), and Theater Media Server (8085).
# =============================================================================

set -euo pipefail

# --- PATHS -------------------------------------------------------------------
SOVEREIGN_HOME="/home/james/stacklabs"
VENV_PYTHON="${SOVEREIGN_HOME}/.venv/bin/python3"
LOG_DIR="${SOVEREIGN_HOME}/logs"

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

echo "[INFO] Commencing surgical restart of Auth, Portal, and Cinema stack..."

# --- PHASE 1: PROCESS CLEANUP ------------------------------------------------
PORTS=(3016 3008 8090 8085)
echo "[INFO] Cleaning up existing processes on ports: ${PORTS[*]}..."

for PORT in "${PORTS[@]}"; do
  PIDS=$(lsof -t -i:$PORT 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "[WARN] Releasing port $PORT (killing PIDs: $PIDS)..."
    kill -15 $PIDS 2>/dev/null || true
    sleep 1
    # Force kill if still lingering
    kill -9 $PIDS 2>/dev/null || true
  fi
done

sleep 2
echo "[OK] Ports cleared."

# --- PHASE 2: CORE BACKEND DAEMONS --------------------------------------------
echo "[INFO] Launching Sovereign Core API & Auth on Port 8090..."
cd "${SOVEREIGN_HOME}"
nohup "${VENV_PYTHON}" scripts/sovereign_core_api.py >> "${LOG_DIR}/sovereign_core_8090.log" 2>&1 &
echo "[OK] Core API initiated (PID: $!). Log: ${LOG_DIR}/sovereign_core_8090.log"

echo "[INFO] Launching Theater Media Server on Port 8085..."
nohup "${VENV_PYTHON}" scripts/theater_media_server.py >> "${LOG_DIR}/theater_media_8085.log" 2>&1 &
echo "[OK] Theater Media Server initiated (PID: $!). Log: ${LOG_DIR}/theater_media_8085.log"

# --- PHASE 3: FRONTEND GATEWAYS -----------------------------------------------
echo "[INFO] Launching Sovereign OS Portal on Port 3016..."
cd "${SOVEREIGN_HOME}/01_Sovereign_Portal"
nohup npm run dev -- --force --port 3016 >> "${LOG_DIR}/vite_portal.log" 2>&1 &
echo "[OK] Portal Frontend initiated (PID: $!). Log: ${LOG_DIR}/vite_portal.log"

echo "[INFO] Launching Sovereign Media UI on Port 3008..."
cd "${SOVEREIGN_HOME}/02_Sovereign_Media"
nohup npm run dev -- --host 0.0.0.0 --port 3008 >> "${LOG_DIR}/vite_cinema.log" 2>&1 &
echo "[OK] Cinema Frontend initiated (PID: $!). Log: ${LOG_DIR}/vite_cinema.log"

# --- PHASE 4: POST-BOOT VERIFICATION -----------------------------------------
echo "[INFO] Waiting 4 seconds for services to bind..."
sleep 4

echo ""
echo "=== SERVICE STATUS CHECK ==="
for PORT in "${PORTS[@]}"; do
  if ss -tlnp 2>/dev/null | grep -q ":${PORT}"; then
    echo "  [ONLINE] Port ${PORT} is bound and active."
  else
    echo "  [WARNING] Port ${PORT} is not bound yet (still booting or error)."
  fi
done
echo "============================"
echo "[SUCCESS] Surgical restart script completed successfully!"
