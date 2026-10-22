#!/bin/bash
export DISPLAY=:0
BASE_DIR="/home/james/.gemini/antigravity/brain/65cf4414-3c74-4db2-8866-41782bca4e15"

URLS=(
    "https://clio.taila01894.ts.net/?domain=PORTAL|portal.png"
    "https://clio.taila01894.ts.net/?domain=MLB&room=dvr|mlb_dvr.png"
    "https://clio.taila01894.ts.net/fanstack_plie_dvr.html|plie_dvr.png"
    "https://clio.taila01894.ts.net/webcam_dvr.html|webcam_dvr.png"
    "https://clio.taila01894.ts.net/?domain=SKEW&room=the_skew|skew.png"
    "https://clio.taila01894.ts.net/scruffys/|scruffys.png"
)

for item in "${URLS[@]}"; do
    url="${item%%|*}"
    filename="${item##*|}"
    echo "Opening $url"
    google-chrome --new-window --kiosk "$url" &
    PID=$!
    sleep 8
    import -window root "$BASE_DIR/$filename"
    kill $PID
    pkill -f "google-chrome"
    sleep 2
done
