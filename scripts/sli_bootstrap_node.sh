#!/usr/bin/env bash
# Sovereign Legal Intelligence (SLI) — Zero-Touch Node Bootstrap Runner
# Ticket: WO-2026-0828-SLI-PILOT-DEPLOYMENT-RUNBOOK

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOVEREIGN_ROOT="$(dirname "$SCRIPT_DIR")"

echo "======================================================================"
echo "⚡ SOVEREIGN LEGAL INTELLIGENCE: ZERO-TOUCH NODE BOOTSTRAP"
echo "======================================================================"

if [ -f "$SOVEREIGN_ROOT/.venv/bin/python3" ]; then
    PYTHON_BIN="$SOVEREIGN_ROOT/.venv/bin/python3"
else
    PYTHON_BIN="python3"
fi

export HISTFILE=/dev/null
"$PYTHON_BIN" "$SCRIPT_DIR/sli_bootstrap_node.py" "$@"
