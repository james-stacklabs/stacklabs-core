#!/bin/bash

# Ensure we're targeting the primary XFCE display
export DISPLAY=:0

# Give the HDMI port a nudge to wake up the TV
xset dpms force on
xset s reset

# Launch native Google Chrome in a standard window.
# Using --incognito to avoid the "Restore Pages" bubble if Chrome was closed ungracefully.
google-chrome-stable --incognito --password-store=basic "https://clio.taila01894.ts.net:3008/cinema-portal/?room=living_room" &
