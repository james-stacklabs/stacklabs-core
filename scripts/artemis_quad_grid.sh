#!/usr/bin/env bash
# ==============================================================================
# StackLabs Artemis Hardware Quad-Grid Video Engine (Mission Control & C120 Sentry)
# Host: Artemis (NVIDIA GTX 1060 6GB Pascal GP106)
# Target: /dev/shm/vfs/mosaic/egress/master_grid.m3u8
# Invariants: 0, 15, 32, 50 (Decoupled Metal Compute)
# ==============================================================================
set -euo pipefail

MOSAIC_DIR="/dev/shm/vfs/mosaic"
INPUTS_DIR="${MOSAIC_DIR}/inputs"
EGRESS_DIR="${MOSAIC_DIR}/egress"
SYN_DIR="/dev/shm/vfs/synthetic"
PID_FILE="${MOSAIC_DIR}/ffmpeg.pid"

mkdir -p "${INPUTS_DIR}" "${EGRESS_DIR}" "${SYN_DIR}"

C120_RTSP="rtsp://argo_pi5:!!Stella1977@192.168.1.191:554/stream1"
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

ACTION="${1:-run}"

if [[ "${ACTION}" == "--stop" || "${ACTION}" == "stop" ]]; then
  echo "🛑 Stopping Artemis Mission Control Grid & Pulse Daemon..."
  /home/james/stacklabs/scripts/mission_control_pulse.sh --stop 2>/dev/null || true
  pkill -f "[s]ynthetic_telemetry_pulse.sh" 2>/dev/null || true
  if [[ -f "${PID_FILE}" ]]; then
    PID=$(cat "${PID_FILE}" || true)
    if [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null; then
      kill "${PID}" 2>/dev/null || true
      sleep 0.5
      kill -9 "${PID}" 2>/dev/null || true
    fi
    rm -f "${PID_FILE}"
  fi
  pkill -f "[m]aster_grid.m3u8" 2>/dev/null || true
  echo "✓ Artemis Mission Control Grid stopped."
  exit 0
fi

# Ensure mission control telemetry pulse daemon is active
if [[ -f "/home/james/stacklabs/scripts/mission_control_pulse.sh" ]]; then
  nohup /home/james/stacklabs/scripts/mission_control_pulse.sh </dev/null >/dev/null 2>&1 &
  PULSE_PID=$!
  disown "${PULSE_PID}" 2>/dev/null || true
  sleep 0.2
fi

# Stop prior FFmpeg encoder before restarting
if [[ -f "${PID_FILE}" ]]; then
  OLD_PID=$(cat "${PID_FILE}" || true)
  if [[ -n "${OLD_PID}" ]] && kill -0 "${OLD_PID}" 2>/dev/null; then
    kill "${OLD_PID}" 2>/dev/null || true
    sleep 0.5
    kill -9 "${OLD_PID}" 2>/dev/null || true
  fi
  rm -f "${PID_FILE}"
fi
pkill -f "[m]aster_grid.m3u8" 2>/dev/null || true

# Clean prior egress segments
rm -f "${EGRESS_DIR}"/*.ts "${EGRESS_DIR}"/*.m3u8 "${EGRESS_DIR}"/*.tmp

if [[ "${ACTION}" == "--recalibrate" || "${ACTION}" == "recalibrate" ]]; then
  Q0="${2:-}"
  Q1="${3:-}"
  Q2="${4:-}"
  Q3="${5:-}"
  DAEMON_MODE=1
elif [[ "${ACTION}" == "--daemon" || "${ACTION}" == "daemon" ]]; then
  Q0="${2:-${C120_RTSP}}"
  Q1="${3:-${SYN_DIR}/quad_agent_radar.txt}"
  Q2="${4:-${SYN_DIR}/quad_cmdb_topo.txt}"
  Q3="${5:-${SYN_DIR}/quad_faas_matrix.txt}"
  DAEMON_MODE=1
else
  Q0="${2:-${C120_RTSP}}"
  Q1="${3:-${SYN_DIR}/quad_agent_radar.txt}"
  Q2="${4:-${SYN_DIR}/quad_cmdb_topo.txt}"
  Q3="${5:-${SYN_DIR}/quad_faas_matrix.txt}"
  DAEMON_MODE=0
fi

echo "⚡ Artemis Pascal GP106 Dynamic Quad Mosaic Engine"
echo "  [Feed 0 Top-Left]     ${Q0:-<DEFAULT>}"
echo "  [Feed 1 Top-Right]    ${Q1:-<DEFAULT>}"
echo "  [Feed 2 Bottom-Left]  ${Q2:-<DEFAULT>}"
echo "  [Feed 3 Bottom-Right] ${Q3:-<DEFAULT>}"
echo "  [Egress Stream]       ${EGRESS_DIR}/master_grid.m3u8"

INPUT_ARGS=()
FILTER_CHAINS=()
IN_IDX=0

for k in 0 1 2 3; do
  var="Q${k}"
  url="${!var}"

  if [[ -z "${url}" || "${url}" == "default" ]]; then
    if [[ ${k} -eq 0 ]]; then
      url="${C120_RTSP}"
    elif [[ ${k} -eq 1 ]]; then
      url="${SYN_DIR}/quad_agent_radar.txt"
    elif [[ ${k} -eq 2 ]]; then
      url="${SYN_DIR}/quad_cmdb_topo.txt"
    elif [[ ${k} -eq 3 ]]; then
      url="${SYN_DIR}/quad_faas_matrix.txt"
    fi
  fi

  # Normalize internal or camera shortcuts
  if [[ "${url}" =~ c120 || "${url}" =~ 192\.168\.1\.191 ]]; then
    url="${C120_RTSP}"
  elif [[ "${url}" =~ ^/api/ ]]; then
    url="http://100.96.77.20:3033${url}"
  fi

  if [[ "${url}" =~ ^rtsp:// ]]; then
    INPUT_ARGS+=(-rtsp_transport tcp -i "${url}")
    FILTER_CHAINS+=("[${IN_IDX}:v]setpts=PTS-STARTPTS,fps=30,scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2,drawtext=fontfile=${FONT}:text='⚡ OPTICAL SENTRY // C120 RTSP':x=20:y=20:fontsize=16:fontcolor=0x00FF88:box=1:boxcolor=0x000000@0.7:boxborderw=6,setsar=1,fifo[v${k}];")
    IN_IDX=$((IN_IDX + 1))
  elif [[ "${url}" =~ ^https?:// ]]; then
    INPUT_ARGS+=(-fflags +genpts+nobuffer+discardcorrupt -probesize 2M -analyzeduration 2M -i "${url}")
    FILTER_CHAINS+=("[${IN_IDX}:v]setpts=PTS-STARTPTS,fps=30,scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2,drawtext=fontfile=${FONT}:text='⚡ QUAD ${k} // LIVE STREAM':x=20:y=20:fontsize=16:fontcolor=0x00F0FF:box=1:boxcolor=0x000000@0.7:boxborderw=6,setsar=1,fifo[v${k}];")
    IN_IDX=$((IN_IDX + 1))
  elif [[ -f "${url}" ]]; then
    COLOR="0x00F0FF"
    [[ ${k} -eq 2 ]] && COLOR="0x00FF88"
    [[ ${k} -eq 3 ]] && COLOR="0xFFB800"
    FILTER_CHAINS+=("color=c=0x0B0D13:s=960x540:r=30,drawtext=fontfile=${FONT}:textfile=${url}:reload=1:expansion=none:x=40:y=40:fontsize=18:fontcolor=${COLOR}:line_spacing=8,setpts=PTS-STARTPTS,setsar=1,fifo[v${k}];")
  else
    COLOR="0x00F0FF"
    FILTER_CHAINS+=("color=c=0x0B0D13:s=960x540:r=30,drawtext=fontfile=${FONT}:text='⚡ QUADRANT ${k} // STANDBY':x=40:y=40:fontsize=18:fontcolor=${COLOR}:line_spacing=8,setpts=PTS-STARTPTS,setsar=1,fifo[v${k}];")
  fi
done

FILTER_COMPLEX="${FILTER_CHAINS[*]} [v0][v1][v2][v3]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0:fill=black:shortest=0[outv]"

FFMPEG_CMD=(
  ffmpeg -y -nostdin
  "${INPUT_ARGS[@]}"
  -filter_complex "${FILTER_COMPLEX}"
  -map "[outv]"
  -c:v h264_nvenc
  -pix_fmt yuv420p
  -profile:v high
  -level 4.1
  -preset p1
  -tune ll
  -rc cbr
  -b:v 3500k
  -maxrate 4000k
  -bufsize 8000k
  -bf 0
  -g 30
  -keyint_min 30
  -forced-idr 1
  -fps_mode cfr
  -an
  -f hls
  -hls_time 2
  -hls_list_size 8
  -hls_flags delete_segments+temp_file
  -hls_segment_filename "${EGRESS_DIR}/segment_%03d.ts"
  "${EGRESS_DIR}/master_grid.m3u8"
)

if [[ "${DAEMON_MODE}" -eq 1 ]]; then
  echo "🚀 Launching Artemis Quad-Grid NVENC daemon into background..."
  nohup "${FFMPEG_CMD[@]}" < /dev/null > "${MOSAIC_DIR}/ffmpeg.log" 2>&1 &
  FFMPEG_PID=$!
  disown "${FFMPEG_PID}" 2>/dev/null || true
  echo "${FFMPEG_PID}" > "${PID_FILE}"
  echo "✓ FFmpeg NVENC daemon active with PID: ${FFMPEG_PID}"
else
  echo $$ > "${PID_FILE}"
  exec "${FFMPEG_CMD[@]}"
fi
