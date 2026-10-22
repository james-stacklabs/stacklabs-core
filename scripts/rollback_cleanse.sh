#!/usr/bin/env bash
# ==============================================================================
# Script: /home/james/stacklabs/scripts/rollback_cleanse.sh
# Purpose: Emergency rollback of StackLabs workspace cleanse. Restores user
#          systemd definitions and restarts services.
# Host: Clio Workstation (Ubuntu Linux, x86_64, user: james)
# ==============================================================================

set -euo pipefail

log() {
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] [ROLLBACK] $*"
}

BACKUP_DIR="$(ls -td /home/james/.stacklabs_cleanse_backup_* 2>/dev/null | head -n 1 || true)"

if [[ -z "${BACKUP_DIR}" || ! -d "${BACKUP_DIR}" ]]; then
    echo "[ERROR] No migration backup directory found under /home/james/.stacklabs_cleanse_backup_*" >&2
    exit 1
fi

log "Rolling back using backup from: ${BACKUP_DIR}"

USER_SERVICES=(
    "clio_queue_watcher.service"
    "faas_game_tailer.service"
    "fanstack-poller.service"
    "fanstack-relay.service"
    "highlight_watcher.service"
    "metal_polygraph.service"
    "scratch-pad-poller.service"
    "sovereign_core_api.service"
    "sovereign_pilot_drop.service"
    "stream_sniper_daemon.service"
    "tmi-daemon.service"
    "carroll-craft.service"
    "davincis-sentinel.service"
    "gmail_promo_sweeper.service"
)

# 1. Stop services
log "Stopping services..."
for svc in "${USER_SERVICES[@]}"; do
    systemctl --user stop "${svc}" 2>/dev/null || true
done

# 2. Restore user systemd definitions
log "Restoring systemd unit files..."
if [[ -d "${BACKUP_DIR}/systemd_user" ]]; then
    for svc_file in "${BACKUP_DIR}/systemd_user"/*.service; do
        if [[ -f "${svc_file}" ]]; then
            svc_name="$(basename "${svc_file}")"
            log "Restoring ~/.config/systemd/user/${svc_name}..."
            cp "${svc_file}" "${HOME}/.config/systemd/user/${svc_name}"
        fi
    done
fi

# 3. Reload daemon and restart
log "Reloading systemd user daemon..."
systemctl --user daemon-reload

log "Restarting services under original configurations..."
for svc in "${USER_SERVICES[@]}"; do
    systemctl --user restart "${svc}" || true
done

log "Verifying rollback state..."
for svc in "${USER_SERVICES[@]}"; do
    if systemctl --user is-active --quiet "${svc}" 2>/dev/null; then
        echo "  ✅ [OK] ${svc} is active (running)"
    else
        echo "  ⚠️ [WARN] ${svc} failed to start"
    fi
done

log "Rollback operation finished."
