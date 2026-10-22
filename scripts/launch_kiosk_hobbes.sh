#!/bin/bash
exec /usr/bin/chromium \
  --no-memcheck \
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
  "https://clio.taila01894.ts.net:3016/?view=tv_projection"
