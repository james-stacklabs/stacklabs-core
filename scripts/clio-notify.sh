#!/usr/bin/env bash
# ==============================================================================
# StackLabs Platform: Clio Workstation Desktop & Audio Notification Dispatcher
# Path: /home/james/stacklabs/scripts/clio-notify.sh
# Usage: clio-notify.sh <success|failure|info> <ticket_name> [details]
# ==============================================================================
set -euo pipefail

STATUS="${1:-info}"
TICKET="${2:-Unknown Ticket}"
DETAILS="${3:-Run completed.}"
LOG_DIR="/home/james/stacklabs/queue/logs"

# Source webhook environment variables if present
if [[ -f /etc/agent_queue/webhooks.env ]]; then
  source /etc/agent_queue/webhooks.env
elif [[ -f /home/james/stacklabs/config/webhooks.env ]]; then
  source /home/james/stacklabs/config/webhooks.env
fi

# GUI/Audio setup for user session
TARGET_USER=$(who | awk '{print $1}' | head -n 1)
USER_ID=$(id -u "${TARGET_USER:-$USER}")
export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${USER_ID}/bus"
export XDG_RUNTIME_DIR="/run/user/${USER_ID}"


send_mobile_alerts() {
  local status="$1"
  local ticket_name="$2"
  local summary="$3"
  local subject=""
  if [[ "$status" == "success" ]]; then
    subject="✅ [Clio] Ticket Complete: ${ticket_name}"
  else
    subject="🚨 [Clio] Ticket FAILED: ${ticket_name}"
  fi

  # Dispatch ntfy push notification
  local ntfy_topic="${NTFY_TOPIC:-stacklabs-pilot-alerts}"
  local priority="default"
  local tags="white_check_mark"
  if [[ "$status" == "failure" ]]; then
    priority="urgent"
    tags="rotating_light"
  fi
  curl -s -H "Title: ${subject}" -H "Priority: ${priority}" -H "Tags: ${tags}" \
    -d "${summary}" "https://ntfy.sh/${ntfy_topic}" >/dev/null 2>&1 || true
}

send_remote_webhook() {
  local ticket_name="$1"
  local summary="$2"

  local latest_log
  latest_log=$(ls -1t "${LOG_DIR}/${ticket_name}"_*.log 2>/dev/null | head -n 1 || true)

  if [[ -n "${WEBHOOK_URL:-}" && "${WEBHOOK_URL}" =~ discord\.com ]]; then
    local log_snippet="No log found."
    if [[ -f "${latest_log}" ]]; then
      log_snippet=$(tail -n 8 "${latest_log}" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n", $0}')
    fi
    local payload=$(cat <<EOF
{
  "username": "Clio Execution Daemon",
  "embeds": [
    {
      "title": "🚨 Ticket Execution Failed: ${ticket_name}",
      "description": "**Summary:** ${summary}\n\n**Log Snippet:**\n\`\`\`text\n${log_snippet}\n\`\`\`",
      "color": 15158332,
      "footer": { "text": "Node: clio | Queue: /home/james/stacklabs/queue/failed/" }
    }
  ]
}
EOF
)
    curl -s -X POST -H "Content-Type: application/json" -d "${payload}" "${WEBHOOK_URL}" >/dev/null 2>&1 || true
  fi
}

if [[ "${STATUS}" == "failure" ]]; then
  # 1. Desktop Notification
  if command -v notify-send >/dev/null 2>&1; then
    send_mobile_alerts "failure" "${TICKET}" "${DETAILS}"
    notify-send -u critical -i dialog-error \
      "🚨 Ticket Failed: ${TICKET}" \
      "${DETAILS}\nCheck: /home/james/stacklabs/queue/failed/" || true
  fi

  # 2. Audio Alert
  if command -v paplay >/dev/null 2>&1; then
    paplay /usr/share/sounds/freedesktop/stereo/dialog-error.oga 2>/dev/null || true
  elif command -v canberra-gtk-play >/dev/null 2>&1; then
    canberra-gtk-play -i dialog-error 2>/dev/null || true
  fi

  # 3. Webhook Dispatch
  if [[ -n "${WEBHOOK_URL:-}" ]]; then
    send_remote_webhook "${TICKET}" "${DETAILS}"
  fi

elif [[ "${STATUS}" == "success" ]]; then
  # 1. Desktop Notification
  if command -v notify-send >/dev/null 2>&1; then
    send_mobile_alerts "success" "${TICKET}" "${DETAILS}"
    notify-send -u normal -i dialog-information \
      "✅ Ticket Complete: ${TICKET}" \
      "${DETAILS}\nArchived to: /home/james/stacklabs/queue/archive/" || true
  fi

  # 2. Audio Chime
  if command -v paplay >/dev/null 2>&1; then
    paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || true
  elif command -v canberra-gtk-play >/dev/null 2>&1; then
    canberra-gtk-play -i complete 2>/dev/null || true
  fi
fi
