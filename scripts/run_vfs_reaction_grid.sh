#!/usr/bin/env bash
# Production VFS Reaction Grid Daemon Runner
# Path: /home/james/stacklabs/scripts/run_vfs_reaction_grid.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python3"
PID_FILE="$ROOT_DIR/data/vfs_reflex.pid"
LOG_FILE="$ROOT_DIR/data/vfs_reflex.log"

export PYTHONPATH="$ROOT_DIR/scripts:$ROOT_DIR"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "VFS Reflex Supervisor is already running (PID $(cat "$PID_FILE"))."
    exit 0
fi

echo "Starting VFS Reflex Supervisor in background..."
if command -v systemd-run >/dev/null 2>&1 && systemctl --user status >/dev/null 2>&1; then
    systemctl --user stop vfs-reflex-watcher.service 2>/dev/null || true
    systemd-run --user --unit=vfs-reflex-watcher --collect \
        --setenv=PYTHONPATH="$PYTHONPATH" \
        "$PYTHON_BIN" "$ROOT_DIR/scripts/vfs_reflex_watcher.py"
    sleep 0.5
else
    nohup "$PYTHON_BIN" "$ROOT_DIR/scripts/vfs_reflex_watcher.py" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
fi

echo "VFS Reflex Supervisor launched with PID $(cat "$PID_FILE"). Logging to $LOG_FILE."
