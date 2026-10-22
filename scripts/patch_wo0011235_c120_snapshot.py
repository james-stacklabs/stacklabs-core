#!/usr/bin/env python3
"""
WO0011235: C120 Optical Sentry Standalone CLI & Cockpit Endpoint Patch
Author: James Carroll (Pilot) & Lead Systems Architect
Node: Clio (100.96.77.20)
Date: 2026-10-18
"""

import os
import stat
import sys
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")
SCRIPTS_DIR = STACKLABS_ROOT / "scripts"
COCKPIT_BP = SCRIPTS_DIR / "blueprints" / "cockpit_bp.py"
LOCAL_BIN = Path.home() / ".local" / "bin"


def deploy_c120_snapshot_script():
    print("📸 Deploying scripts/c120_snapshot.py...")
    script_path = SCRIPTS_DIR / "c120_snapshot.py"
    
    script_content = '''#!/usr/bin/env python3
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
'''
    script_path.write_text(script_content)
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("✔ scripts/c120_snapshot.py deployed and made executable.")

    # Create ~/.local/bin/c120 symlink
    LOCAL_BIN.mkdir(parents=True, exist_ok=True)
    symlink_path = LOCAL_BIN / "c120"
    if symlink_path.is_symlink() or symlink_path.exists():
        symlink_path.unlink()
    symlink_path.symlink_to(script_path)
    print(f"✔ Symlinked {symlink_path} -> {script_path}")


def patch_cockpit_blueprint():
    print("🔧 Patching scripts/blueprints/cockpit_bp.py...")
    if not COCKPIT_BP.exists():
        print(f"ERROR: {COCKPIT_BP} not found", file=sys.stderr)
        sys.exit(1)

    code = COCKPIT_BP.read_text(encoding="utf-8")
    if "/api/cockpit/c120/snapshot" in code:
        print("✔ /api/cockpit/c120/snapshot route already present.")
        return

    route_code = '''

@bp.route('/api/cockpit/c120/snapshot', methods=['GET', 'POST'])
def api_cockpit_c120_snapshot():
    """
    Serve live Tapo C120 optical sentry snapshot.
    - If ?raw=1 or Accept contains image/*, returns raw JPEG bytes.
    - Otherwise, returns JSON metadata.
    """
    try:
        from scripts.c120_snapshot import capture_snapshot
        stream_idx = int(request.args.get('stream', 1))
        ts_flag = request.args.get('timestamped', '0') in ('1', 'true', 'yes')
        res = capture_snapshot(stream=stream_idx, timestamped=ts_flag)

        is_raw = (
            request.args.get('raw') == '1' or
            request.args.get('view') == '1' or
            'image/' in request.headers.get('Accept', '')
        )

        if is_raw:
            with open(res['path'], 'rb') as f:
                img_bytes = f.read()
            return img_bytes, 200, {
                'Content-Type': 'image/jpeg',
                'Cache-Control': 'no-cache, no-store, must-revalidate'
            }

        return jsonify(res)
    except Exception as e:
        logger.error(f"C120 snapshot error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500
'''
    COCKPIT_BP.write_text(code + route_code, encoding="utf-8")
    print("✔ Added /api/cockpit/c120/snapshot route to cockpit_bp.py.")


def main():
    deploy_c120_snapshot_script()
    patch_cockpit_blueprint()
    print("🚀 Patch WO0011235 completed successfully.")


if __name__ == "__main__":
    main()
