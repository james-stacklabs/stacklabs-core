#!/usr/bin/env bash
# ==============================================================================
# StackLabs Platform: Pre-FaaS Legacy App Evacuation Script
# Path: /home/james/stacklabs/scripts/sweep_pre_faas_apps.sh
# Purpose: Evacuate pre-FaaS legacy app directories to sovereign_archive
# ==============================================================================
set -euo pipefail

ARCHIVE_DIR="/home/james/sovereign_archive/legacy_apps"
mkdir -p "${ARCHIVE_DIR}"

TARGETS=(
  "/home/james/stacklabs/apps/portal"
  "/home/james/stacklabs/33_FanStack_Lite"
  "/home/james/stacklabs/apps/mard_studio"
  "/home/james/stacklabs/apps/carroll_craft"
)

echo "[INIT] Starting Pre-FaaS application sweep..."

for TARGET in "${TARGETS[@]}"; do
  if [[ -d "${TARGET}" ]]; then
    BASENAME=$(basename "${TARGET}")
    DEST="${ARCHIVE_DIR}/${BASENAME}"
    echo "[EVACUATE] Moving ${TARGET} -> ${DEST}"
    if [[ -d "${DEST}" ]]; then
      echo "[WARN] Destination ${DEST} already exists. Creating timestamped backup..."
      DEST="${DEST}_$(date +%Y%m%d_%H%M%S)"
    fi
    mv "${TARGET}" "${DEST}"
  else
    echo "[SKIP] Target not found: ${TARGET}"
  fi
done

echo "[SUCCESS] Pre-FaaS application sweep complete. Relics evacuated to ${ARCHIVE_DIR}."
