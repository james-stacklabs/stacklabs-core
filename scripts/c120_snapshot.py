#!/usr/bin/env python3
"""
StackLabs C120 Optical Sentry Snapshot Utility
Captures a live high-resolution or fast sub-second frame from the Tapo C120 RTSP stream.
Path: /home/james/stacklabs/scripts/c120_snapshot.py
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

DEFAULT_RTSP = "rtsp://argo_pi5:!!Stella1977@192.168.1.191:554/stream1"
FAST_RTSP = "rtsp://argo_pi5:!!Stella1977@192.168.1.191:554/stream2"
DEFAULT_OUTPUT = Path("/home/james/stacklabs/pilot_drops/photos") / "c120_latest.jpg"
SHM_OUTPUT = Path("/dev/shm/vfs/cameras") / "c120_latest.jpg"


def capture_snapshot(output_path=DEFAULT_OUTPUT, stream=1, timestamped=False, shm_copy=True, timeout=5):
    rtsp_url = DEFAULT_RTSP if stream == 1 else FAST_RTSP
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-frames:v", "1",
        "-update", "1",
        str(output_path)
    ]

    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=True
    )

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Snapshot capture failed: {output_path} is empty or missing")

    size = output_path.stat().st_size
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_path = None
    if timestamped:
        ts_path = output_path.parent / f"PXL_C120_{ts_str}.jpg"
        shutil.copy2(output_path, ts_path)

    if shm_copy:
        SHM_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output_path, SHM_OUTPUT)

    return {
        "status": "success",
        "path": str(output_path),
        "size_bytes": size,
        "timestamp": ts_str,
        "timestamped_path": str(ts_path) if ts_path else None,
        "stream": stream
    }


def main():
    parser = argparse.ArgumentParser(description="Tapo C120 Optical Sentry Frame Grabber")
    parser.add_argument("-s", "--stream", type=int, choices=[1, 2], default=1, help="RTSP stream index (1=1440p high-res, 2=360p fast)")
    parser.add_argument("-o", "--output", type=str, default=str(DEFAULT_OUTPUT), help="Output image path")
    parser.add_argument("-t", "--timestamped", action="store_true", help="Also save timestamped archive copy in pilot_drops/photos/")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    try:
        result = capture_snapshot(
            output_path=args.output,
            stream=args.stream,
            timestamped=args.timestamped
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[C120 OPTICAL SENTRY] Snapshot captured: {result['path']} ({result['size_bytes']} bytes)")
            if result.get("timestamped_path"):
                print(f"  -> Archive copy: {result['timestamped_path']}")
    except Exception as e:
        print(f"[ERROR] Snapshot failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
