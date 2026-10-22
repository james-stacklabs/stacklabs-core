#!/usr/bin/env bash
# ==============================================================================
# Sovereign OS: Clio Workstation Full-Screen Aerospace HUD
# ==============================================================================
set -euo pipefail

SESSION_NAME="clio-hud"
QUEUE_DIR="/home/james/sovereign_inbox/queue"
LOG_DIR="${QUEUE_DIR}/logs"
CURRENT_LOG="${LOG_DIR}/current.log"

mkdir -p "${LOG_DIR}"
touch "${CURRENT_LOG}"

# If session already exists, attach directly
if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
  echo "[INFO] Attaching to existing ${SESSION_NAME} session..."
  if [ -t 0 ]; then
    tmux attach-session -t "${SESSION_NAME}"
  else
    echo "[INFO] Running non-interactively; session ${SESSION_NAME} already exists."
  fi
  exit 0
fi

# Window 0: Full-Screen Aerospace Sports & Forge Cockpit
tmux new-session -d -s "${SESSION_NAME}" -n "Cockpit"
tmux send-keys -t "${SESSION_NAME}:0" \
  "python3 /home/james/stacklabs/scripts/clio_aerospace_hud.py" C-m

# Window 1: Dedicated Clean agy Log Stream (Accessible via Ctrl-b 1)
tmux new-window -t "${SESSION_NAME}" -n "LogStream"
tmux send-keys -t "${SESSION_NAME}:1" \
  "echo '=== [CLIO LIVE AGY EXECUTION STREAM: LOGSTREAM WINDOW] ==='; tail -F '${CURRENT_LOG}'" C-m

# Default to Window 0 (Cockpit)
tmux select-window -t "${SESSION_NAME}:0"

# Styling & Mouse Support
tmux set-option -t "${SESSION_NAME}" status on
tmux set-option -t "${SESSION_NAME}" status-interval 2
tmux set-option -t "${SESSION_NAME}" status-style "bg=#121620,fg=#94A3B8"
tmux set-option -t "${SESSION_NAME}" status-left "#[fg=#10B981,bold] CLIO FORGE #[default]│ "
tmux set-option -t "${SESSION_NAME}" status-right "#[fg=#38BDF8]%Y-%m-%d %H:%M EDT #[default]"
tmux set-option -t "${SESSION_NAME}" mouse on

if [ -t 0 ]; then
  tmux attach-session -t "${SESSION_NAME}"
else
  echo "[INFO] Session ${SESSION_NAME} created and running in background."
fi
