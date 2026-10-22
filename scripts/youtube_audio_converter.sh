#!/bin/bash
AUDIO="/home/james/stacklabs/dna/dropzone/daily_21042026/VEO_REVIEW_QUEUE/The_math_of_the_2026_Mets_meltdown.m4a"
VIDEO="/home/james/stacklabs/dna/dropzone/daily_21042026/VEO_REVIEW_QUEUE/flow_stich_add_audio/Wardy_Barf_desk_202604210953.mp4"
OUTPUT="/home/james/stacklabs/dna/dropzone/daily_21042026/YOUTUBE_READY_The_math_of_the_2026_Mets.mp4"

echo "=== CONVERTING AUDIO TO YOUTUBE MP4 ==="
# We use the wide shot video, loop it indefinitely, lay the audio over it, and end exactly when audio finishes.
ffmpeg -stream_loop -1 -i "$VIDEO" -i "$AUDIO" -c:v libx264 -c:a aac -shortest "$OUTPUT" -y -v quiet
echo "[SUCCESS] Saved to $OUTPUT"
