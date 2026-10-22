#!/bin/bash
# Sovereign Temporal Advantage Forensic Rendering - GMT Overlay
# Orchestrated by Antigravity
# Target: Node .74 (Pi 5)

set -e

SOURCE_VIDEO="/home/james/stacklabs/dna/media/hailo_dropzone/PXL_20260407_202905479.mp4"
FILENAME="PXL_20260407_202905479.mp4"
PEGASUS_HOST="pegasus"
REMOTE_WORKSPACE="/tmp/forensic_workspace"
OUTPUT_FILENAME="LINDOR_SCORE_FORENSIC.mp4"
EVIDENCE_DIR="/home/james/stacklabs/dna/media/uat_evidence"

# Ensure evidence directory exists
mkdir -p "$EVIDENCE_DIR"

echo "[1/4] Preparing Remote Workspace on Node .74..."
ssh $PEGASUS_HOST "mkdir -p $REMOTE_WORKSPACE"

echo "[2/4] Beaming Source Artifact ($FILENAME) to Pegasus..."
scp "$SOURCE_VIDEO" $PEGASUS_HOST:$REMOTE_WORKSPACE/

echo "[3/4] Engaging NVENC H264 Hardware Render Engine..."
# True GMT Start: 2026-04-07 20:29:05.479 UTC -> Epoch: 1775593745
OVERLAY_COMMAND="ffmpeg -y -i $REMOTE_WORKSPACE/$FILENAME \
-vf \"\
drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf: \
text='[TRUE GMT\: %{pts\:gmtime\:1775593745}]': \
fontcolor=yellow: fontsize=54: box=1: boxcolor=black@0.6: boxborderw=10: x=W-tw-40: y=40, \
drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf: \
text='[SOVEREIGN MESH TELEMETRY\: In play, run(s)]': \
fontcolor=magenta: fontsize=64: box=1: boxcolor=black@0.6: boxborderw=10: x=(w-tw)/2: y=H-th-60, \
drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf: \
text='[LATENCY ADVANTAGE\: ~45 SECONDS OVER PEACOCK/MLB.TV]': \
fontcolor=cyan: fontsize=48: box=1: boxcolor=black@0.6: boxborderw=10: x=40: y=40 \
\" \
-c:v libx264 -preset slow -crf 22 -c:a copy $REMOTE_WORKSPACE/$OUTPUT_FILENAME"

ssh $PEGASUS_HOST "$OVERLAY_COMMAND"

echo "[4/4] Retrieving Rendered Artifact..."
scp $PEGASUS_HOST:$REMOTE_WORKSPACE/$OUTPUT_FILENAME "$EVIDENCE_DIR/"

echo "================================================================"
echo " [SUCCESS] Forensic render complete."
echo " Artifact available at: $EVIDENCE_DIR/$OUTPUT_FILENAME"
echo "================================================================"
