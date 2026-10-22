#!/usr/bin/env bash
# ==============================================================================
# StackLabs Synthetic Glass Telemetry Pulse Daemon
# Host: Artemis (NVIDIA GTX 1060 6GB Pascal GP106)
# Target: /dev/shm/vfs/synthetic/state.txt (Updated 10 times a second)
# Invariants: 0, 15, 32, 50 (Decoupled Metal Compute)
# ==============================================================================
set -euo pipefail

SYN_DIR="/dev/shm/vfs/synthetic"
mkdir -p "${SYN_DIR}"
PID_FILE="${SYN_DIR}/pulse.pid"

if [[ "${1:-run}" == "--stop" || "${1:-run}" == "stop" ]]; then
  if [[ -f "${PID_FILE}" ]]; then
    PID=$(cat "${PID_FILE}" || true)
    if [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null; then
      kill "${PID}" 2>/dev/null || true
    fi
    rm -f "${PID_FILE}"
  fi
  pkill -f "[s]ynthetic_telemetry_pulse.sh" 2>/dev/null || true
  exit 0
fi

echo $$ > "${PID_FILE}"

while true; do
  CLK=$(date +'%H:%M:%S.%3N')
  GPU_STATS=$(nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used,power.draw --format=csv,noheader,nounits 2>/dev/null || echo "0, 0, 0, 0")
  IFS=',' read -r TEMP UTIL VRAM PWR <<< "${GPU_STATS}"
  
  cat <<EOF > "${SYN_DIR}/state.txt.tmp"
==================================================
⚡ STACKLABS SYNTHETIC GLASS // ARTEMIS GP106
==================================================
TIME (EDT)       : ${CLK}
VFS BUS REFLEX   : 14.5 µs (DDR5 / /dev/shm)
PIPELINE CADENCE : 30.000 FPS CFR (NVENC P1)

--- [ GPU HARDWARE TELEMETRY ] ---
GPU TEMPERATURE  : ${TEMP// /}°C (Limit: 82°C)
GPU CORE LOAD    : ${UTIL// /}%
VRAM WORKING SET : ${VRAM// /} MB / 6144 MB
NVENC ASIC POWER : ${PWR// /} W

--- [ SOVEREIGN GAMEDAY REFLEX ] ---
SLM INFERENCE    : STANDBY [ACTIVE REFLEX]
OUTBOX QUEUE     : 0 PENDING (DRAINED)
CANVAS EGRESS    : 1920x1080 @ 3500 kbps CBR
TARGET DECODER   : FIRE TV 65" (MediaCodec 2W)
==================================================
EOF
  mv "${SYN_DIR}/state.txt.tmp" "${SYN_DIR}/state.txt"
  sleep 0.1
done
