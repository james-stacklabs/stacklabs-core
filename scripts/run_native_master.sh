#!/bin/bash

# Clean stage
rm -f /home/james/stacklabs/dna/archives/uat_evidence/EXHIBIT_LINDOR_*.png 
rm -f /home/james/stacklabs/dna/archives/uat_evidence/EXHIBIT_PICKOFF_*.png 
rm -f /home/james/stacklabs/dna/archives/uat_evidence/EXHIBIT_GORMAN_*.png 

echo "Initializing consolidated Single-Node render with priority logic..."

nice -n -10 bash /home/james/stacklabs/scripts/extract_frames.sh --force -nostdin -i /home/james/stacklabs/dna/media/hailo_dropzone/PXL_20260405_214946603.mp4 -vf "fps=5,scale=1280:-1,drawtext=text='[STREAM\: PIRATE] [REALTIME\: %{pts\:localtime\:1515430000}] [DELAY\: MANUAL_SYNC]':x=10:y=10:fontsize=24:fontcolor=cyan:box=1:boxcolor=black@0.5" -frames:v 300 -y /home/james/stacklabs/dna/archives/uat_evidence/EXHIBIT_LINDOR_%03d.png > /home/james/stacklabs/dna/logs/ext_lindor.log 2>&1 < /dev/null &

nice -n -10 bash /home/james/stacklabs/scripts/extract_frames.sh --force -nostdin -i /home/james/stacklabs/dna/media/hailo_dropzone/PXL_20260405_234212704.mp4 -vf "fps=5,scale=1280:-1,drawtext=text='[STREAM\: PEACOCK] [REALTIME\: %{pts\:localtime\:1515436932}] [LAG\: +23.0s (EST)]':x=10:y=10:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.5" -frames:v 300 -y /home/james/stacklabs/dna/archives/uat_evidence/EXHIBIT_PICKOFF_%03d.png > /home/james/stacklabs/dna/logs/ext_pick.log 2>&1 < /dev/null &

nice -n -10 bash /home/james/stacklabs/scripts/extract_frames.sh --force -nostdin -i /home/james/stacklabs/dna/media/hailo_dropzone/PXL_20260405_234242970.mp4 -vf "fps=5,scale=1280:-1,drawtext=text='[STREAM\: PEACOCK] [REALTIME\: %{pts\:localtime\:1515436962}] [LAG\: +20.9s (EST)]':x=10:y=10:fontsize=24:fontcolor=magenta:box=1:boxcolor=black@0.5" -frames:v 300 -y /home/james/stacklabs/dna/archives/uat_evidence/EXHIBIT_GORMAN_%03d.png > /home/james/stacklabs/dna/logs/ext_gorman.log 2>&1 < /dev/null &

wait
echo "SINGLE-NODE RENDER COMPLETE."
