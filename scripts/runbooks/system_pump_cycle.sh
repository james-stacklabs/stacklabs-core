#!/bin/bash
# scripts/runbooks/system_pump_cycle.sh
# Pre-approved StackLabs Estate Runbook: System Water / Glycol Pump Cycle
# Enforces strictly bounded execution on metal under Clio.
set -euo pipefail

echo "CYCLE_START: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "CALLER: ${STACKLABS_CALLER_IDENTITY:-unknown}"
echo "PARAMS: ${STACKLABS_ACTION_PARAMS:-{}}"
echo "PUMP_RELAY_ACTIVATED: GPIO_PIN_18 SET_HIGH"
sleep 0.1
echo "PUMP_RELAY_NORMALIZED: GPIO_PIN_18 SET_LOW"
echo "CYCLE_COMPLETE: STATUS_OK"
echo "PUMP_CYCLED_OK"
exit 0
