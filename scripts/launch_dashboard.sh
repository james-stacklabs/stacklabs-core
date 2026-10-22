#!/bin/bash

# Configuration
SESSION_NAME="sovereign_dashboard"
PORT=8089
TTYD_BIN="/home/james/stacklabs/ttyd_aarch"

# Ensure ttyd binary exists
if [ ! -f "$TTYD_BIN" ]; then
    echo "ttyd_aarch binary not found in apiary root!"
    exit 1
fi

# Kill any existing old dashboard sessions
tmux kill-session -t $SESSION_NAME 2>/dev/null
pkill -f ttyd_aarch

# Start new background tmux session
tmux new-session -d -s $SESSION_NAME

# Split window - bottom 20% for instructions
tmux split-window -v -p 20 -t $SESSION_NAME:0

# Setup the Top Pane (My Ops Screen)
tmux send-keys -t $SESSION_NAME:0.0 'clear' C-m
tmux send-keys -t $SESSION_NAME:0.0 'echo "==============================================="' C-m
tmux send-keys -t $SESSION_NAME:0.0 'echo " SOVEREIGN OPERATIONS CHASSIS - NODE .73"' C-m
tmux send-keys -t $SESSION_NAME:0.0 'echo "==============================================="' C-m
tmux send-keys -t $SESSION_NAME:0.0 'uptime' C-m

# Setup the Bottom Pane (Pilot Comm-Link)
tmux send-keys -t $SESSION_NAME:0.1 'clear' C-m
tmux send-keys -t $SESSION_NAME:0.1 'echo "==============================================="' C-m
tmux send-keys -t $SESSION_NAME:0.1 'echo " PILOT COMM-LINK (Type instructions below)"' C-m
tmux send-keys -t $SESSION_NAME:0.1 'echo "==============================================="' C-m

# Select top pane as default active so any user clicks don't distract me if they just want to watch
tmux select-pane -t $SESSION_NAME:0.0

# Launch TTYD Web Proxy in background, making it writable with -W
echo "Spooling Web Terminal on Port $PORT..."
nohup $TTYD_BIN -W -p $PORT tmux attach -t $SESSION_NAME > /home/james/stacklabs/logs/ttyd_dashboard.log 2>&1 &

echo "Dashboard actively broadcasting on http://127.0.0.1:$PORT (and Tailscale nodes)"
