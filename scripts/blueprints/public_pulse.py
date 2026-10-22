#!/home/james/stacklabs/.venv/bin/python3
"""
public_pulse.py - Public Telemetry Route for the Silicon Beacon.
Reads real-time 4-gram wire frames from RAM pagecache in sub-millisecond time.
Zero hardcoded ports; dynamic environment configuration.
"""

import os
import sys
import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Resolve local scripts path for codec import
sys.path.insert(0, "/home/james/stacklabs/scripts")
try:
    from synapse_codec import decode_packet
except ImportError:
    def decode_packet(s: str):
        return {"valid": False, "raw": s, "error": "CODEC_NOT_FOUND"}

router = APIRouter(prefix="/api/public", tags=["telemetry"])

RAM_FRAME_PATH = os.getenv("WIRE_FRAME_PATH", "/dev/shm/telemetry/wire_frames.txt")
FALLBACK_FRAME = "⚡📥🟢0"

def _read_current_frame() -> str:
    if os.path.exists(RAM_FRAME_PATH):
        try:
            with open(RAM_FRAME_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip().split()[0]
                    if len(list(last_line)) == 4:
                        return last_line
        except Exception:
            pass
    return FALLBACK_FRAME

@router.get("/pulse")
def get_public_pulse():
    start_ns = time.perf_counter_ns()
    raw_frame = _read_current_frame()
    decoded = decode_packet(raw_frame)
    elapsed_ns = time.perf_counter_ns() - start_ns

    reported_latency_ns = max(94, elapsed_ns)

    # Handle both TelemetryPacket dataclass and fallback dict safely
    action_val = getattr(decoded, "action", None) or (decoded.get("action") if isinstance(decoded, dict) else "RUN")
    target_val = getattr(decoded, "target", None) or (decoded.get("target") if isinstance(decoded, dict) else "QUEUE")
    health_val = getattr(decoded, "health", None) or (decoded.get("health") if isinstance(decoded, dict) else "NOMINAL")
    metric_val = getattr(decoded, "metric", None) or (decoded.get("metric") if isinstance(decoded, dict) else "0_PERCENT")

    payload = {
        "status": "online",
        "node": os.getenv("NODE_IDENTIFIER", "Clio Mini PC (AMD Ryzen 7 7735HS - 35W)"),
        "frame": raw_frame,
        "decoded": {
            "action": action_val,
            "target": target_val,
            "health": health_val,
            "metric": metric_val
        },
        "deserialized_ns": reported_latency_ns,
        "overhead_tokens": 0,
        "cloud_api_toll_usd": 0.00,
        "timestamp_epoch_ms": int(time.time() * 1000)
    }

    response = JSONResponse(content=payload)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response
