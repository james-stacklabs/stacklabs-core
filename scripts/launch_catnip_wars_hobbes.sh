#!/bin/bash
# ==============================================================================
# Sovereign OS - Remote Catnip Wars Deployer for Hobbes (Node .114)
# ==============================================================================
# This script runs on Clio to:
#  1. Wake Eileen's TV via HDMI CEC on Hobbes (HDMI Port 1).
#  2. Force the TV input to active source (switches it to Hobbes).
#  3. Nudge the X11 screen saver and DPMS signaling to prevent sleep.
#  4. Launch Chromium in Kiosk Mode with strict low-memory optimization flags.
# ==============================================================================

TARGET="james@100.88.5.122"
PASS="!!Stella1977"
GAME_URL="https://clio.taila01894.ts.net:7300/"

echo -e "\e[1;36m========================================================\e[0m"
echo -e "\e[1;36m  SOVEREIGN OS: DEPLOYING CATNIP WARS ON HOBBES (Node .114) \e[0m"
echo -e "\e[1;36m========================================================\e[0m"

# 1. Connectivity Check
echo -e "\e[1;33m[*] Checking Tailscale connection to Hobbes ($TARGET)...\e[0m"
ping -c 2 -W 3 100.88.5.122 > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "\e[1;31m[!] Error: Hobbes is unreachable on Tailscale. Verify tailscale status.\e[0m"
    exit 1
fi
echo -e "\e[1;32m[+] Hobbes is online and responding!\e[0m"

# 2. Wake the TV via HDMI CEC & Switch active source
echo -e "\e[1;33m[*] Sending HDMI CEC Wake Command & Active Source Switch (HDMI Port 1)...\e[0m"
sshpass -p "$PASS" ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no "$TARGET" \
  "echo 'on 0' | cec-client -s -d 1 >/dev/null 2>&1 && echo 'as' | cec-client -s -d 1 >/dev/null 2>&1"
if [ $? -ne 0 ]; then
    echo -e "\e[1;31m[!] CEC Nudge warning: cec-client could not interact with HDMI port.\e[0m"
else
    echo -e "\e[1;32m[+] TV Wake & Active Source commands successfully transmitted.\e[0m"
fi

# 3. Nudge Display DPMS & Launch Chromium with Performance Parameters
echo -e "\e[1;33m[*] Initializing optimized browser session on Hobbes...\e[0m"
# Chromium flags optimized for Pi Zero 2 W's 512MB RAM constraints:
# - Bypasses crashes, disables low-end lagging, optimizes GPU rasterization.
LAUNCH_CMD="export DISPLAY=:0 && \
xset dpms force on && \
xset s reset && \
xset s off && \
xset s noblank && \
xset -dpms && \
killall chromium-browser > /dev/null 2>&1 || true && \
nohup chromium-browser \
  --kiosk \
  --no-sandbox \
  --disable-low-end-device-mode \
  --disable-gpu-rasterization \
  --enable-only-gpu-rasterization \
  --ignore-gpu-blocklist \
  --noerrdialogs \
  --disable-infobars \
  --disable-translate \
  --start-maximized \
  --password-store=basic \
  --incognito \
  --disable-session-crashed-bubble \
  \"$GAME_URL\" > /tmp/hobbes_kiosk.log 2>&1 &"

sshpass -p "$PASS" ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no "$TARGET" "$LAUNCH_CMD"
if [ $? -ne 0 ]; then
    echo -e "\e[1;31m[!] Error deploying browser kiosk on Hobbes.\e[0m"
    exit 1
fi

echo -e "\e[1;32m[+] SUCCESS! Catnip Wars dashboard deployed in kiosk mode.\e[0m"
echo -e "\e[1;36m========================================================\e[0m"
