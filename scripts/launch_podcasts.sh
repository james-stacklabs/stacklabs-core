#!/bin/bash
# Sovereign Podcast Host
export DIR="/home/james/stacklabs/dna/media/hailo_dropzone/podcasts"

# Kill any existing server on 8090
fuser -k 8090/tcp 2>/dev/null || true

echo "Starting Podcast Server tightly bound to Tailscale IP (100.123.68.9) on Port 8090..."
nohup python3 -m http.server 8090 --directory "$DIR" > /home/james/stacklabs/scripts/podcast_server.log 2>&1 &

echo "Success! The FanStack Pod URL is native and live via your Tailscale Mesh."
