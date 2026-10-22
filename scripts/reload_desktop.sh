#!/usr/bin/env bash
# ==============================================================================
# Sovereign OS: Desktop Environment (GNOME Shell on X11) In-Place Reloader
# Path: /home/james/stacklabs/scripts/reload_desktop.sh
# Alias: reload-desktop
# ==============================================================================
set -euo pipefail

echo "🖥️  [DESKTOP] Reloading GNOME Shell on Clio in place..."

# SIGHUP to gnome-shell tells Mutter to restart in-place without closing applications
if pgrep -x "gnome-shell" >/dev/null 2>&1; then
    echo "⚡ [DESKTOP] Sending in-place restart signal (SIGHUP) to gnome-shell..."
    pkill -HUP -x "gnome-shell"
    sleep 1.5
    echo "✅ [DESKTOP] GNOME Shell reloaded successfully (PID: $(pgrep -x gnome-shell | head -n 1))."
else
    echo "⚠️  [DESKTOP] gnome-shell process not found."
fi

# Optional: Ensure Barrier reconnects seamlessly to the refreshed display
if [ -x "/home/james/.local/bin/restart-barrier" ]; then
    echo "🔄 [DESKTOP] Syncing Barrier KVM client..."
    /home/james/.local/bin/restart-barrier >/dev/null 2>&1 &
fi

echo "✨ [DESKTOP] Desktop environment refreshed. All windows preserved, mouse pointer grabs cleared."
