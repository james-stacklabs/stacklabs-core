#!/bin/bash

PYTHON_SCRIPT="/home/james/stacklabs/scripts/deploy_game_room.py"

if [ "$1" == "today" ]; then
    python3 /home/james/stacklabs/scripts/sync_mlb_schedule.py --today
    exit 0
fi

if [ -z "$1" ]; then
    echo "FanStack MLB Operations Pipeline"
    echo "Usage:"
    echo "  ./fanstack_mlb.sh today"
    echo "  ./fanstack_mlb.sh <GAME_PK> [--chaos]"
    exit 1
fi

GAME_PK="$1"
shift

echo "Running Yardbarker Entropy Pump to refresh ambient context..."
python3 "/home/james/stacklabs/scripts/yardbarker_entropy_pump.py"
echo "------------------------------------------------------------"

python3 "$PYTHON_SCRIPT" "$GAME_PK" "$@"
