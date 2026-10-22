#!/bin/bash

# The Final "No-Excuses" YouTube Uploader Script
# Explicit stream mapping to isolate the beautiful Veo puppet video and the NotebookLM audio, discarding ALL garbage streams.

AUDIO="/home/james/stacklabs/dna/dropzone/daily_21042026/VEO_REVIEW_QUEUE/The_math_of_the_2026_Mets_meltdown.m4a"
VIDEO="/home/james/stacklabs/dna/dropzone/daily_21042026/VEO_REVIEW_QUEUE/flow_stich_add_audio/Wardy_Barf_desk_202604210953.mp4"
OUTPUT="/home/james/stacklabs/dna/dropzone/daily_21042026/YOUTUBE_MASTER_WARDY_BARF.mp4"

echo "=== ISOLATING STREAMS AND RENDERING FINAL YOUTUBE MASTER ==="

# HOW IT WORKS:
# -stream_loop -1 loops the video infinitely.
# -map 0:v:0 explicitly selects ONLY the video sequence from the Wardy/Barf File (throwing away the Veo audio).
# -map 1:a:0 explicitly selects ONLY the audio sequence from the NotebookLM File.
# -shortest cuts the video exactly when the NotebookLM audio ends.

ffmpeg -stream_loop -1 -i "$VIDEO" -i "$AUDIO" \
    -map 0:v:0 -map 1:a:0 \
    -c:v libx264 -c:a aac \
    -pix_fmt yuv420p \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" \
    -shortest "$OUTPUT" -y -v quiet

echo "=== SUCCESS ==="
echo "File located at: $OUTPUT"
