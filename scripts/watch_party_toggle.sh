#!/bin/bash
# ==============================================================================
# Sovereign OS — Watch Party Dev Server Fleet Pruning & Toggle Controller
# Path: /home/james/stacklabs/scripts/watch_party_toggle.sh
# Governed by: Rule Zero (Clio owns metal) | WO0010372
# Controls:
#   - Port 3009: FanStack Creator Studio (15_FanStack)
#   - Port 3010: FanStack Sovereign Sports / Quad TV Wall (19_Sovereign_Sports)
# ==============================================================================

set -e

PORT_3009=3009
PORT_3010=3010
DIR_3009="/home/james/stacklabs/15_FanStack"
DIR_3010="/home/james/stacklabs/19_Sovereign_Sports"
LOGS_DIR="/home/james/stacklabs/logs"
mkdir -p "$LOGS_DIR"

start_port_3009() {
    local pids=$(lsof -ti:"$PORT_3009" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "[!] Port $PORT_3009 is already running (PID: $pids). Skipping start."
    else
        echo "[+] Launching FanStack Creator Studio (Port $PORT_3009)..."
        (cd "$DIR_3009" && nohup npm run dev -- --host 0.0.0.0 --port "$PORT_3009" >> "$LOGS_DIR/vite_fanstack.log" 2>&1 &)
        sleep 2
        local new_pid=$(lsof -ti:"$PORT_3009" 2>/dev/null || true)
        if [ -n "$new_pid" ]; then
            echo "[✔] FanStack Creator Studio started on Port $PORT_3009 (PID: $new_pid)."
        else
            echo "[⚠️] Failed to verify Port $PORT_3009 listener. Check $LOGS_DIR/vite_fanstack.log"
        fi
    fi
}

start_port_3010() {
    local pids=$(lsof -ti:"$PORT_3010" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "[!] Port $PORT_3010 is already running (PID: $pids). Skipping start."
    else
        echo "[+] Launching FanStack Sovereign Sports / Quad TV Wall (Port $PORT_3010)..."
        (cd "$DIR_3010" && nohup npm run dev -- --host 0.0.0.0 --port "$PORT_3010" >> "$LOGS_DIR/vite_sports.log" 2>&1 &)
        sleep 2
        local new_pid=$(lsof -ti:"$PORT_3010" 2>/dev/null || true)
        if [ -n "$new_pid" ]; then
            echo "[✔] FanStack Sovereign Sports started on Port $PORT_3010 (PID: $new_pid)."
        else
            echo "[⚠️] Failed to verify Port $PORT_3010 listener. Check $LOGS_DIR/vite_sports.log"
        fi
    fi
}

stop_port() {
    local port="$1"
    local name="$2"
    local pattern="$3"
    echo "[+] Terminating $name on Port $port..."
    if [ -n "$pattern" ]; then
        pkill -9 -f "$pattern" 2>/dev/null || true
    fi
    fuser -k -9 "${port}/tcp" 2>/dev/null || true
    sleep 1
    local pids=$(lsof -ti:"$port" 2>/dev/null || true)
    if [ -z "$pids" ]; then
        echo "[✔] $name on Port $port terminated successfully."
    else
        kill -9 $pids 2>/dev/null || true
        echo "[✔] $name on Port $port force-terminated."
    fi
}

status_port() {
    local port="$1"
    local name="$2"
    local pids=$(lsof -ti:"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "  🟢 $name (Port $port): ACTIVE (PID: $pids)"
    else
        echo "  ⚪ $name (Port $port): HIBERNATING (Offline)"
    fi
}

case "${1:-status}" in
    start)
        echo "🚀 Starting Watch Party Servers (Ports 3009 and 3010)..."
        start_port_3009
        start_port_3010
        ;;
    stop)
        echo "🛑 Pruning Watch Party Servers (Ports 3009 and 3010)..."
        stop_port "$PORT_3009" "FanStack Creator (3009)" "15_FanStack"
        stop_port "$PORT_3010" "FanStack Sports (3010)" "19_FanStackArena|19_Sovereign_Sports"
        ;;
    status)
        echo "📊 Watch Party Server Status:"
        status_port "$PORT_3009" "FanStack Creator Studio"
        status_port "$PORT_3010" "FanStack Sovereign Sports"
        ;;
    restart)
        echo "🔄 Bouncing Watch Party Servers..."
        stop_port "$PORT_3009" "FanStack Creator (3009)" "15_FanStack"
        stop_port "$PORT_3010" "FanStack Sports (3010)" "19_FanStackArena|19_Sovereign_Sports"
        sleep 1
        start_port_3009
        start_port_3010
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac
