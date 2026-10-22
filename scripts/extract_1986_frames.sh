#!/bin/bash
# Sovereign Video Extractor
# Runs ffmpeg to rip 1 frame per second to perfectly sync pre-Statcast ROM payloads.

VIDEO_PATH="/home/james/stacklabs/dna/media/hailo_dropzone/YTDown.com_YouTube_1986-World-Series-Game-6-Red-Sox-_-Mets_Media_B0jV_kNs2p0_001_480p.mp4"
FRAMES_DIR="/home/james/stacklabs/dna/media/hailo_dropzone/frames_1986"

echo "[SYS] Initializing Temporal Frame Extraction..."

mkdir -p "$FRAMES_DIR"

# Extracts 1 frame per second (-vf fps=1)
ffmpeg -i "$VIDEO_PATH" -vf fps=1 "$FRAMES_DIR/thumb_%04d.jpg" -hide_banner

echo "[SYS] Extraction complete. Review frames in $FRAMES_DIR to note the exact second constraints for the ROM."
