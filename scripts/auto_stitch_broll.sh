#!/bin/bash
# Sovereign Flowmercial Assembler
# Cleans Veo 3.1 videos (stripping native audio/British accents), normalizes the resolution, and stitches them into a looping B-Roll track.

WORK_DIR="/home/james/stacklabs/dna/dropzone/daily_21042026/VEO_REVIEW_QUEUE/flow_stich_add_audio"
AUDIO_FILE="/home/james/stacklabs/dna/dropzone/daily_21042026/Billionaire_hubris_versus_the_Costanza_Protocol.m4a"
OUTPUT_FILE="${WORK_DIR}/FINAL_BROADCAST_CUT.mp4"

cd "$WORK_DIR"
echo "=== INITIATING B-ROLL SANITIZATION & STITCHING ==="

# 1. Clean and normalize each video (strip the hallucinated audio, normalize framerate/size)
counter=1
> fileList.txt
for video in *.mp4; do
    # Skip output or already processed files
    if [[ "$video" == "clean_"* ]] || [[ "$video" == "FINAL_"* ]]; then continue; fi
    
    echo "[+] Processing: $video"
    ffmpeg -i "$video" -an -c:v libx264 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -r 30 "clean_${counter}.mp4" -y -v quiet
    echo "file 'clean_${counter}.mp4'" >> fileList.txt
    ((counter++))
done

# 2. Build the extended loop sequence
echo "[+] Extending loop matrix for full podcast duration..."
> extendedList.txt
# Copy the short sequence out 10 times to ensure we have enough B-Roll time for a 6-minute audio file
for i in {1..10}; do
    cat fileList.txt >> extendedList.txt
done

# 3. Final Stitch and Audio Overlay
echo "[+] Assembling Final Broadcast Timeline..."
if [[ -f "$AUDIO_FILE" ]]; then
    # Stitch video and overlay audio, snapping cut to the shortest stream (so the video ends when the audio ends)
    ffmpeg -f concat -safe 0 -i extendedList.txt -i "$AUDIO_FILE" -c:v copy -c:a aac -shortest "$OUTPUT_FILE" -y -v quiet
    echo "[SUCCESS] Audio-synced broadcast saved to: $OUTPUT_FILE"
else
    # Output silent B-roll master if audio isn't hooked up yet
    ffmpeg -f concat -safe 0 -i extendedList.txt -c:v copy "$OUTPUT_FILE" -y -v quiet
    echo "[SUCCESS] Silent B-Roll Master saved to: $OUTPUT_FILE"
fi

# Cleanup
rm clean_*.mp4 fileList.txt extendedList.txt

echo "=== M.A.R.D ENGINE PIPELINE COMPLETE ==="
ls -lh "$OUTPUT_FILE"
