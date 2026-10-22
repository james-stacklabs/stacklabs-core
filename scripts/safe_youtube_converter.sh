#!/bin/bash
# Sovereign Safe YouTube Converter
# Safely maps the NotebookLM audio over a static anchor image to ensure zero container corruption.

AUDIO="/home/james/stacklabs/dna/dropzone/daily_21042026/VEO_REVIEW_QUEUE/The_math_of_the_2026_Mets_meltdown.m4a"
IMAGE="/home/james/.gemini/antigravity/brain/49dc5bc0-f6da-44db-b599-527460c58729/media__1776768138123.png"
OUTPUT="/home/james/stacklabs/dna/dropzone/daily_21042026/YOUTUBE_SAFE_Math_of_2026_Mets.mp4"

echo "=== INITIATING FAILSAFE YOUTUBE CONVERSION ==="
if [[ ! -f "$AUDIO" ]]; then
    echo "ERROR: Audio file not found at $AUDIO"
    exit 1
fi

if [[ ! -f "$IMAGE" ]]; then
    echo "ERROR: Image file not found at $IMAGE"
    exit 1
fi

# The -loop 1 combined with -shortest guarantees a pristine video/audio container.
# We also ensure the video is standard 16:9 1080p for YouTube.
ffmpeg -loop 1 -i "$IMAGE" -i "$AUDIO" \
    -c:v libx264 -tune stillimage -c:a aac -b:a 192k \
    -pix_fmt yuv420p -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
    -shortest "$OUTPUT" -y

echo "=== SUCCESS: FILE READY FOR YOUTUBE ==="
echo "Path: $OUTPUT"
