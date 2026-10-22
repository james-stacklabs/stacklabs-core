#!/usr/bin/env bash
# scripts/fanstack_daily_prep.sh — Daily Slate Ingress and Roll Call Setup
set -eo pipefail

GAME_ID="${1:-824874}"
CROSS_POLLINATE=false
if [ "${2:-}" = "--cross-pollinate" ] || [ "${2:-}" = "-cp" ]; then
    CROSS_POLLINATE=true
fi

ROLL_CALL_PORT="${ROLL_CALL_PORT:-8000}"

echo "[*] Running FanStack Daily Prep for Game ID: $GAME_ID"

# Ingress Phase: Fetch today's schedule from MLB API
echo "[*] Ingress Phase: Fetching fresh MLB daily schedule..."
mkdir -p /home/james/stacklabs/data
curl -s "https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1" > /home/james/stacklabs/data/today_schedule.json

# Seeding Phase: Run the seeder script
echo "[*] Seeding Phase: Seeding MLB schedule into DB..."
/home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/seed_schedule.py --file /home/james/stacklabs/data/today_schedule.json

echo "[*] Synchronizing Sports Ground Truth..."
/home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/sync_sports_ground_truth.py --sport ALL

# Checkpoint Phase: Run directory sync and notify UI
echo "[*] Checkpoint Phase: Running sync to Google Drive..."
bash /home/james/stacklabs/scripts/sync_to_gdrive.sh -gd || true
echo "[*] Notifying Roll Call UI via system broadcast..."
curl -s -X POST "http://127.0.0.1:${ROLL_CALL_PORT}/api/system/broadcast" || true

# Step 1: Run setup_all_rooms.py to stage the game room in the DB
/home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/setup_all_rooms.py "$GAME_ID"

# Step 2: Override seating to place advocates in game_persona and m2m_persona_room
if [ "$CROSS_POLLINATE" = true ]; then
    echo "[*] Cross-pollinating room seating..."
    /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/seat_cross_pollinated.py
else
    echo "[*] Seating default advocates..."
    /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/seat_advocates.py
fi

echo "[✅] FanStack Daily Prep completed successfully for Game ID: $GAME_ID"
