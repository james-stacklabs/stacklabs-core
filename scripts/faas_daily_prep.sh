#!/usr/bin/env bash
# faas_daily_prep.sh
# Tool #67 // FaaS Daily Prep CLI Wrapper
set -e

SOVEREIGN_HOME="/home/james/stacklabs"
VENV_PYTHON="${SOVEREIGN_HOME}/.venv/bin/python3"
if [ -x "$VENV_PYTHON" ]; then
    PY_BIN="$VENV_PYTHON"
else
    PY_BIN="python3"
fi

exec "$PY_BIN" "${SOVEREIGN_HOME}/scripts/faas_daily_prep.py" "$@"
