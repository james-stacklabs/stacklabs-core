#!/usr/bin/env bash
# ==============================================================================
# Sovereign OS: Barrier KVM Client Quick-Restart Script
# Path: /home/james/stacklabs/scripts/restart_barrier.sh
# Alias: restart-barrier
# ==============================================================================
set -euo pipefail

SERVER_HOST="artemis-1.taila01894.ts.net"
SERVER_PORT="24800"

echo "🔄 [BARRIER] Restarting Barrier KVM client on Clio..."

# 1. Kill any existing or hung barrierc processes
if pgrep -f "barrierc" >/dev/null 2>&1; then
    echo "🛑 [BARRIER] Terminating stale barrierc process..."
    pkill -9 -f "barrierc" || true
    sleep 1
fi

# 2. Check if the server on Artemis is reachable over Tailscale
echo "📡 [BARRIER] Probing ${SERVER_HOST}:${SERVER_PORT}..."
if nc -zv -w 3 "${SERVER_HOST}" "${SERVER_PORT}" >/dev/null 2>&1; then
    echo "✔ [BARRIER] Artemis Barrier server is reachable!"
else
    echo "⚠️ [BARRIER WARN] Could not reach ${SERVER_HOST}:${SERVER_PORT}."
    echo "   Ensure Barrier is running on your Artemis laptop (Server mode, Port 24800)."
fi

# 3. Launch fresh barrierc daemon with --no-xinitthreads to prevent clipboard thread deadlocks
echo "🚀 [BARRIER] Launching barrierc daemon (with --no-xinitthreads)..."
/usr/bin/barrierc --daemon --no-tray --disable-crypto --no-xinitthreads "${SERVER_HOST}:${SERVER_PORT}"

sleep 1

# 4. Verify running PID
if pgrep -f "barrierc" >/dev/null 2>&1; then
    PID=$(pgrep -f "barrierc" | head -n 1)
    echo "✅ [BARRIER] Connected! barrierc is running (PID: ${PID})."
    echo "   Mouse and keyboard should now seamlessly glide to Clio's screen."
else
    echo "❌ [BARRIER ERROR] barrierc failed to start."
    exit 1
fi
