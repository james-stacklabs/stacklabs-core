#!/bin/bash
# vertex_toggle.sh - Toggle the Vertex AI / Gemini 2.5 Flash override

BURN_FILE="/home/james/stacklabs/config/vertex_burn.on"

if [ -f "$BURN_FILE" ]; then
    rm "$BURN_FILE"
    echo "=========================================================="
    echo "🔥 VERTEX BURN MODE DISABLED 🔥"
    echo "AI Personas will now fall back to their local Edge models."
    echo "=========================================================="
else
    touch "$BURN_FILE"
    echo "=========================================================="
    echo "⚡ VERTEX BURN MODE ENABLED ⚡"
    echo "ALL AI Personas are now hard-locked to Gemini 2.5 Flash."
    echo "Consuming Enterprise Promotional Credits!"
    echo "=========================================================="
fi
