#!/bin/bash
# Sovereign SceneBuilder Audio Dubber
# Strips the hallucinated Veo native audio out of the video and perfectly layers your clean TTS audio track over it.

# --- EDIT THESE PATHS WHEN YOU HAVE YOUR AUDIO FILE ---
# 1. Point this to the 48-second video you exported from Flow:
VIDEO_INPUT="/home/james/stacklabs/dna/dropzone/daily_21042026/VEO_REVIEW_QUEUE/Sovereign_fanstack_48s_202604211214_ohkrj.mp4"

# 2. Point this to the audio file you generate from ElevenLabs/TTS:
AUDIO_INPUT="/home/james/stacklabs/dna/dropzone/daily_21042026/VEO_REVIEW_QUEUE/character_voices.m4a"

# 3. This is what the final, perfect YouTube-ready file will be named:
OUTPUT_FILE="/home/james/stacklabs/dna/dropzone/daily_21042026/FINAL_SCENEBUILDER_YOUTUBE_READY.mp4"
# ------------------------------------------------------

echo "=== INITIATING SCENEBUILDER AUDIO DUB ==="

if [[ ! -f "$VIDEO_INPUT" ]]; then
    echo "[!] ERROR: Video file not found: $VIDEO_INPUT"
    exit 1
fi

if [[ ! -f "$AUDIO_INPUT" ]]; then
    echo "[!] ERROR: Audio file not found: $AUDIO_INPUT"
    echo "Make sure you update the AUDIO_INPUT variable in this script once you download the audio!"
    exit 1
fi

# WHAT THIS DOES:
# -map 0:v:0   -> Takes ONLY the video stream from the video file (stripping Flow's native audio)
# -map 1:a:0   -> Takes ONLY the audio stream from your audio file
# -c:v copy    -> Super-fast copy of the video (Zero quality loss, takes 1 second instead of 10 minutes)
# -c:a aac     -> Ensures YouTube compliance for the audio
# -shortest    -> Cuts the final video exactly when the shortest file (video or audio) ends.

ffmpeg -i "$VIDEO_INPUT" -i "$AUDIO_INPUT" \
    -map 0:v:0 -map 1:a:0 \
    -c:v copy -c:a aac -b:a 192k \
    -shortest "$OUTPUT_FILE" -y -v quiet

echo "=== SUCCESS! DUB COMPLETE ==="
echo "Your masterpiece is ready at: $OUTPUT_FILE"
ls -lh "$OUTPUT_FILE"
