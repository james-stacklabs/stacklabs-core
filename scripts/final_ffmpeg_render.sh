#!/bin/bash
set -e

DROPZONE="/home/james/stacklabs/dna/dropzone/daily_21042026"
AUDIO="${DROPZONE}/Billionaire_hubris_versus_the_Costanza_Protocol.m4a"
OUTPUT="${DROPZONE}/FINAL_Billionaire_Hubris.mp4"

cd "$DROPZONE"

echo "=== INITIATING M.A.R.D. COMPILE SEQUENCE ==="

# 1. Intro Hook [0:00 - 0:45] (45 sec)
echo "[1/6] Rendering Intro..."
ffmpeg -loop 1 -i ../../notebook_lm_exports/GEM_DRIVE_UPLOAD_PACK/media__1776768138123.png -t 45 -c:v libx264 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -pix_fmt yuv420p -r 30 seg1.mp4 -y -v quiet

# 2. The Brooks Exception [0:45 - 2:10] (85 sec)
echo "[2/6] Rendering Barf sequence..."
ffmpeg -stream_loop -1 -i VEO_RENDER_1_barf_panic.mp4 -t 85 -c:v libx264 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -r 30 seg2.mp4 -y -v quiet

# 3. Data Defense [2:10 - 3:30] (80 sec)
echo "[3/6] Rendering Analytics Data..."
ffmpeg -loop 1 -i ../../notebook_lm_exports/GEM_DRIVE_UPLOAD_PACK/media__1776770825897.png -t 80 -c:v libx264 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -pix_fmt yuv420p -r 30 seg3.mp4 -y -v quiet

# 4. Umpire Bias [3:30 - 4:45] (75 sec)
echo "[4/6] Rendering Umpire sequence..."
ffmpeg -stream_loop -1 -i VEO_RENDER_2_umpire_stare.mp4 -t 75 -c:v libx264 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -r 30 seg4.mp4 -y -v quiet

# 5. Costanza's Revenge [4:45 - 5:20] (35 sec)
echo "[5/6] Rendering Hubris chart..."
ffmpeg -loop 1 -i ../../notebook_lm_exports/GEM_DRIVE_UPLOAD_PACK/media__1776771584443.png -t 35 -c:v libx264 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -pix_fmt yuv420p -r 30 seg5.mp4 -y -v quiet

# 6. The Outro [5:20 - End] (40 sec)
echo "[6/6] Rendering Terry Defeat sequence..."
ffmpeg -stream_loop -1 -i VEO_RENDER_3_terry_defeat.mp4 -t 45 -c:v libx264 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -r 30 seg6.mp4 -y -v quiet

# 7. Concatenate all segments dynamically
echo "[7/7] Splicing into Master Timeline..."
cat << 'CONCAT' > concat_list.txt
file 'seg1.mp4'
file 'seg2.mp4'
file 'seg3.mp4'
file 'seg4.mp4'
file 'seg5.mp4'
file 'seg6.mp4'
CONCAT

ffmpeg -f concat -safe 0 -i concat_list.txt -i "$AUDIO" -c:v copy -c:a aac -shortest "$OUTPUT" -y -v quiet

# Cleanup temporary segments
rm seg1.mp4 seg2.mp4 seg3.mp4 seg4.mp4 seg5.mp4 seg6.mp4 concat_list.txt

echo "=== BROADCAST RENDERED: FINAL_Billionaire_Hubris.mp4 ==="
ls -lh "$OUTPUT"
