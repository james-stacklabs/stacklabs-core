#!/bin/bash
# Remove any partial local files to restart clean on Pegasus
mkdir -p /tmp/uat_evidence
rm -f /tmp/uat_evidence/EXHIBIT_PICKOFF_*.png /tmp/uat_evidence/EXHIBIT_GORMAN_*.png /tmp/uat_evidence/EXHIBIT_LINDOR_*.png

echo "[*] Triggering FULL DUAL-CLOCK RENDERS on x86_64 Pegasus Worker..."

# LINDOR (PIRATE)
bash /tmp/extract_frames.sh --force -nostdin -i /tmp/PXL_20260405_214946603.mp4 \
-vf "fps=5,scale=1280:-1,drawtext=text='[STREAM\: PIRATE] [REALTIME\: %{pts\:localtime\:1515430000}] [DELAY\: MANUAL_SYNC]':x=10:y=10:fontsize=24:fontcolor=cyan:box=1:boxcolor=black@0.5" \
-frames:v 300 -y /tmp/uat_evidence/EXHIBIT_LINDOR_%03d.png > /tmp/ext_lindor.log 2>&1 < /dev/null &

# PICKOFF (PEACOCK A)
bash /tmp/extract_frames.sh --force -nostdin -i /tmp/PXL_20260405_234212704.mp4 \
-vf "fps=5,scale=1280:-1,drawtext=text='[STREAM\: PEACOCK] [REALTIME\: %{pts\:localtime\:1515436932}] [LAG\: +23.0s (EST)]':x=10:y=10:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.5" \
-frames:v 300 -y /tmp/uat_evidence/EXHIBIT_PICKOFF_%03d.png > /tmp/ext_pick.log 2>&1 < /dev/null &

# GORMAN (PEACOCK B)
bash /tmp/extract_frames.sh --force -nostdin -i /tmp/PXL_20260405_234242970.mp4 \
-vf "fps=5,scale=1280:-1,drawtext=text='[STREAM\: PEACOCK] [REALTIME\: %{pts\:localtime\:1515436962}] [LAG\: +20.9s (EST)]':x=10:y=10:fontsize=24:fontcolor=magenta:box=1:boxcolor=black@0.5" \
-frames:v 300 -y /tmp/uat_evidence/EXHIBIT_GORMAN_%03d.png > /tmp/ext_gorman.log 2>&1 < /dev/null &

wait
echo "[SYS] Master Pegasus extraction completed!"
