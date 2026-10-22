#!/bin/bash

# Define the ports used by our servers
PORTS=(3000 3016 3024 3008 8085 8083)

echo "Stopping Vite servers on specific ports..."
for PORT in "${PORTS[@]}"; do
  # Find PIDs listening on the port and kill them safely
  PIDS=$(lsof -t -i:$PORT)
  if [ -n "$PIDS" ]; then
    echo "Killing processes on port $PORT"
    kill -9 $PIDS
  fi
done

# Wait to ensure ports are completely released
sleep 2

echo "Starting 01_Sovereign_Portal on port 3016..."
cd /home/james/stacklabs/01_Sovereign_Portal
nohup npm run dev -- --force --port 3016 > /tmp/vite_portal.log 2>&1 &

echo "Starting 14_SamTracker backend daemon on port 8083..."
cd /home/james/stacklabs
nohup .venv/bin/python3 scripts/sam_tracker_server.py > /tmp/sam_tracker.log 2>&1 &

echo "Starting 14_SamTracker Vite frontend on port 3024..."
cd /home/james/stacklabs/14_SamTracker
nohup npm run dev -- --force --port 3024 > /tmp/vite_sam.log 2>&1 &

echo "Starting 02_Sovereign_Media on port 3008..."
cd /home/james/stacklabs/02_Sovereign_Media
nohup npm run dev -- --host 0.0.0.0 --port 3008 > /tmp/vite_cinema.log 2>&1 &

echo "Starting theater_media_server.py on port 8085..."
cd /home/james/stacklabs
nohup python3 scripts/theater_media_server.py > /tmp/theater_media_8085.log 2>&1 &

echo "All services initiated in the background!"

# Dynamic StackLabs Micro-Frontend Bootstrap Rules
echo "Igniting isolated StackLabs LLC Site on Port 3000..."
cd /home/james/stacklabs/16_StackLabsLLC
nohup npm run dev -- --force --host 0.0.0.0 --port 3000 > /tmp/vite_stacklabs.log 2>&1 &
