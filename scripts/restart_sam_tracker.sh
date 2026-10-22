#!/bin/bash
# Dedicated, surgical restart script for SamTracker.
# Restarts only SamTracker (ports 3004 and 8083) without touching port 3000 (Sovereign Portal) or port 3008 (Cinema).

echo "Stopping SamTracker services..."
FRONTEND_PIDS=$(lsof -t -i:3024)
if [ -n "$FRONTEND_PIDS" ]; then
  echo "Killing SamTracker frontend (port 3024)..."
  kill -9 $FRONTEND_PIDS
fi

BACKEND_PIDS=$(lsof -t -i:8083)
if [ -n "$BACKEND_PIDS" ]; then
  echo "Killing SamTracker backend daemon (port 8083)..."
  kill -9 $BACKEND_PIDS
fi

sleep 1

echo "Starting 14_SamTracker backend daemon on port 8083..."
cd /home/james/stacklabs
nohup .venv/bin/python3 scripts/sam_tracker_server.py > /tmp/sam_tracker.log 2>&1 &

echo "Starting 14_SamTracker Vite frontend on port 3024..."
cd /home/james/stacklabs/14_SamTracker
nohup npm run dev -- --force --port 3024 > /tmp/vite_sam.log 2>&1 &

echo "SamTracker services surgically restarted!"
