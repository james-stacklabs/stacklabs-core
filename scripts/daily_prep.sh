#!/bin/bash
# Sovereign FanStack Daily Prep Sequence
# Version 3.1 (Aligned with /fanstack_daily_prep SDLC workflow)
# Fast daily slate roll call with optional sub-flags (--audit, --tweet, --onboard, --full)

set -e

# Enforce strict headless sandbox variables
export DISPLAY=""
export PLAYWRIGHT_HEADLESS=true

SOVEREIGN_HOME="/home/james/stacklabs"
VENV_PYTHON="${SOVEREIGN_HOME}/.venv/bin/python3"
LOG_FILE="/tmp/daily_prep.log"

RUN_AUDIT=false
RUN_TWEET=false
RUN_ONBOARD=false

for arg in "$@"; do
    case $arg in
        --audit|-pa|--persona-audit)
            RUN_AUDIT=true
            ;;
        --tweet|-tb|--twitter-bot)
            RUN_TWEET=true
            ;;
        --onboard|-ob|--persona-onboarder)
            RUN_ONBOARD=true
            ;;
        --full|-all|--all)
            RUN_AUDIT=true
            RUN_TWEET=true
            RUN_ONBOARD=true
            ;;
    esac
done

echo "============================================="
echo "  SOVEREIGN FANSTACK DAILY PREP INITIATED"
echo "  $(date)"
echo "============================================="

echo "[1/5] Running Yardbarker Entropy Pump..."
"${VENV_PYTHON}" "${SOVEREIGN_HOME}/scripts/yardbarker_entropy_pump.py"

echo "[2/5] Sweeping Gmail for Promos..."
"${VENV_PYTHON}" "${SOVEREIGN_HOME}/scripts/gmail_promo_sweeper.py"

echo "[3/5] Fetching MLB Schedule & Resolving Streams..."
"${VENV_PYTHON}" "${SOVEREIGN_HOME}/scripts/sync_mlb_schedule.py"
"${VENV_PYTHON}" "${SOVEREIGN_HOME}/scripts/stream_url_resolver.py"
"${VENV_PYTHON}" "${SOVEREIGN_HOME}/scripts/mlb_news_crawler.py"

if [ "$RUN_AUDIT" = true ]; then
    echo "[OPTIONAL] Performing Vertex Persona Audit..."
    "${VENV_PYTHON}" "${SOVEREIGN_HOME}/scripts/vertex_persona_audit.py"
else
    echo "[SKIP] Vertex Persona Audit (--audit / -pa flag not passed)."
fi

echo "[4/5] Staging Rooms and Personas in DB..."
"${VENV_PYTHON}" "${SOVEREIGN_HOME}/scripts/setup_all_rooms.py"

echo "[5/5] Restarting Sovereign Stack Daemons (Cold-Boot)..."
bash "${SOVEREIGN_HOME}/scripts/restart_stack.sh"

if [ "$RUN_TWEET" = true ]; then
    echo "[OPTIONAL] Deploying Barf Twitter Bot..."
    "${VENV_PYTHON}" "${SOVEREIGN_HOME}/scripts/barf_twitter_bot.py"
else
    echo "[SKIP] Barf Twitter Bot (--tweet / -tb flag not passed)."
fi

if [ "$RUN_ONBOARD" = true ]; then
    echo "[OPTIONAL] Running SDLC Persona Onboarder..."
    "${VENV_PYTHON}" "${SOVEREIGN_HOME}/scripts/sdlc_persona_onboarder.py"
else
    echo "[SKIP] SDLC Persona Onboarder (--onboard / -ob flag not passed)."
fi

echo "============================================="
echo "  DAILY PREP COMPLETE"
echo "  $(date)"
echo "============================================="

