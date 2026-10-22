#!/bin/bash
echo "[*] Initializing NVENC 60-FPS Temporal Burn on GTX 980..."

mkdir -p /home/james/stacklabs/dna/archives/uat_evidence

# Gorman
ffmpeg -y -hwaccel cuda -i /home/james/stacklabs/dna/media/hailo_dropzone/PXL_20260405_234242970.mp4 -vf "fps=60,scale=1280:-1,drawtext=text='[STREAM\: PEACOCK] [REALTIME\: %{pts\:localtime\:1515436962}] [LAG\: +20.9s (EST)]':x=10:y=10:fontsize=24:fontcolor=magenta:box=1:boxcolor=black@0.5,format=yuv420p" -c:v h264_nvenc -preset p6 -tune hq -b:v 15M -c:a copy /home/james/stacklabs/dna/archives/uat_evidence/GORMAN_60FPS_BURN.mp4 > /home/james/stacklabs/dna/logs/nvenc_gorman.log 2>&1 &
PID1=$!

# Pickoff
ffmpeg -y -hwaccel cuda -i /home/james/stacklabs/dna/media/hailo_dropzone/PXL_20260405_234212704.mp4 -vf "fps=60,scale=1280:-1,drawtext=text='[STREAM\: PEACOCK] [REALTIME\: %{pts\:localtime\:1515436932}] [LAG\: +23.0s (EST)]':x=10:y=10:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.5,format=yuv420p" -c:v h264_nvenc -preset p6 -tune hq -b:v 15M -c:a copy /home/james/stacklabs/dna/archives/uat_evidence/PICKOFF_60FPS_BURN.mp4 > /home/james/stacklabs/dna/logs/nvenc_pickoff.log 2>&1 &
PID2=$!

echo "[*] WATCHDOG ACTIVE: Logging GPU Vitals to CMDB_GPU_BURN.log..."
echo "TIMESTAMP, GPU_UTIL, GPU_TEMP" > /home/james/stacklabs/dna/logs/CMDB_GPU_BURN.log
while kill -0 $PID1 2>/dev/null || kill -0 $PID2 2>/dev/null; do
    TIMESTAMP=$(date +"%T")
    STATS=$(nvidia-smi --query-gpu=utilization.gpu,temperature.gpu --format=csv,noheader,nounits)
    echo "$TIMESTAMP, $STATS" >> /home/james/stacklabs/dna/logs/CMDB_GPU_BURN.log
    sleep 2
done

wait
echo "[SYS] FORENSIC BURN COMPILED OUT NATIVELY."
