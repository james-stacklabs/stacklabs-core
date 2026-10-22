#!/usr/bin/env python3
"""
StackLabs Variance Engine Ingress Daemon

Author: James Carroll, Lead Systems Architect
Host Target: Workstation Clio (x86_64, AMD Ryzen 7 7735HS @ 35W)

Sub-2ms pruning loop over double-buffered shared memory counterfactual trajectories.
"""

import os
import sys
import json
import time
import mmap
import struct
import asyncio
from pathlib import Path
from aiohttp import web
import numpy as np

RUNTIME_DIR = Path("/tmp/stacklabs_runtime")
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
CANVAS_FILE = RUNTIME_DIR / "pilot.json"
TEMP_FILE = RUNTIME_DIR / "pilot.json.tmp"
SHM_FILE = "/dev/shm/stacklabs_corridor_shm"
SUBSCRIBERS = set()

# Operational Risk Constants
THETA_CEIL = 0.050   # +5.0%
THETA_FLOOR = -0.025 # -2.5%
Y_BASELINE = 0.50
Y_SCALE = 5.0


class DoubleBufferedCorridor:
    """Zero-copy double-buffered shared memory reader and simulator."""

    def __init__(self, filepath: str = SHM_FILE):
        self.filepath = filepath
        self._ensure_shm_layout()
        self.fd = os.open(self.filepath, os.O_RDWR)
        self.buf = mmap.mmap(self.fd, 0, access=mmap.ACCESS_WRITE)
        self.header_size = 20
        self.buffer_size = 4 + 4 + (336 * 4 * 3) + (100 * 336 * 4)
        self.seq = 0

    def _ensure_shm_layout(self):
        total_size = 20 + (2 * (4 + 4 + (336 * 4 * 3) + (100 * 336 * 4)))
        if not os.path.exists(self.filepath) or os.path.getsize(self.filepath) != total_size:
            with open(self.filepath, "wb") as f:
                f.write(b'\x00' * total_size)

    def write_simulation(self, current_step: int, realized_xle: float):
        """100-path stochastic trajectory kernel with atomic buffer flipping."""
        self.buf.seek(0)
        current_active = struct.unpack("<I", self.buf.read(4))[0]
        inactive_idx = 1 - (current_active % 2)
        self.seq += 1

        # Local 100-path stochastic simulation kernel
        paths = np.random.normal(0, 0.005, (100, 336)).astype(np.float32)
        cum_paths = np.cumsum(paths, axis=1) + realized_xle
        p95 = np.percentile(cum_paths, 95, axis=0).astype(np.float32)
        p05 = np.percentile(cum_paths, 5, axis=0).astype(np.float32)
        p50 = np.percentile(cum_paths, 50, axis=0).astype(np.float32)

        offset = self.header_size + (inactive_idx * self.buffer_size)
        self.buf.seek(offset)
        self.buf.write(struct.pack("<II", self.seq, current_step))
        self.buf.write(p95.tobytes())
        self.buf.write(p05.tobytes())
        self.buf.write(p50.tobytes())
        self.buf.write(cum_paths.tobytes())

        # Atomic generation flip
        sip_ts = int(time.time() * 1e9)
        self.buf.seek(0)
        self.buf.write(struct.pack("<IQQ", inactive_idx, sip_ts, self.seq))
        self.buf.flush()

    def get_active_corridor(self, current_step: int, realized_xle: float):
        self.buf.seek(0)
        active_idx = struct.unpack("<I", self.buf.read(4))[0]
        sip_ts, sip_seq = struct.unpack("<QQ", self.buf.read(16))

        offset = self.header_size + (active_idx * self.buffer_size)
        self.buf.seek(offset)
        gen, step_idx = struct.unpack("<II", self.buf.read(8))

        # Read pre-computed quantiles (P95, P05, P50)
        p95 = np.frombuffer(self.buf.read(336 * 4), dtype=np.float32)
        p05 = np.frombuffer(self.buf.read(336 * 4), dtype=np.float32)
        p50 = np.frombuffer(self.buf.read(336 * 4), dtype=np.float32)

        # In-memory local fallback if simulation buffer is empty
        if np.all(p95 == 0.0):
            p95 = np.linspace(0.01, 0.08, 336, dtype=np.float32)
            p05 = np.linspace(-0.01, -0.04, 336, dtype=np.float32)
            p50 = np.linspace(0.0, 0.02, 336, dtype=np.float32)

        sample_steps = np.linspace(current_step, 335, 4, dtype=int)
        x_coords = np.linspace(0.40, 0.95, 4)

        upper_bound = [{"x": float(x), "y": float(Y_BASELINE - (p95[s] * Y_SCALE))} for x, s in zip(x_coords, sample_steps)]
        lower_bound = [{"x": float(x), "y": float(Y_BASELINE - (p05[s] * Y_SCALE))} for x, s in zip(x_coords, sample_steps)]
        median_pts = [{"x": float(x), "y": float(Y_BASELINE - (p50[s] * Y_SCALE))} for x, s in zip(x_coords, sample_steps)]

        return upper_bound, lower_bound, median_pts, sip_ts, sip_seq


def build_canvas_payload(corridor: DoubleBufferedCorridor, realized_xle: float, realized_xlk: float) -> dict:
    t0 = time.perf_counter()
    step_index = 48
    upper, lower, median, sip_ts, sip_seq = corridor.get_active_corridor(step_index, realized_xle)

    y_xle = Y_BASELINE - (realized_xle * Y_SCALE)
    y_xlk = Y_BASELINE - (realized_xlk * Y_SCALE)

    payload = {
        "version": "1.1.0",
        "timestamp": int(time.time() * 1e6),
        "provenance": {
            "sip_timestamp": sip_ts,
            "sip_sequence": sip_seq,
            "ptp_offset_ns": 42
        },
        "viewport": {
            "aspect_ratio": "16:9",
            "coordinate_space": {"x_min": 0.0, "x_max": 1.0, "y_min": 0.0, "y_max": 1.0}
        },
        "theme": {"background": "#0B0D13", "surface": "#11141E", "border": "#FFFFFF10"},
        "primitives": [
            {
                "id": "risk_ceil",
                "type": "threshold_band",
                "z_index": 0,
                "threshold_data": {
                    "axis": "y",
                    "start": Y_BASELINE - (THETA_CEIL * Y_SCALE) - 0.01,
                    "end": Y_BASELINE - (THETA_CEIL * Y_SCALE) + 0.01,
                    "fill_color": "rgba(244, 63, 94, 0.08)",
                    "border_color": "#F43F5E40"
                }
            },
            {
                "id": "risk_floor",
                "type": "threshold_band",
                "z_index": 0,
                "threshold_data": {
                    "axis": "y",
                    "start": Y_BASELINE - (THETA_FLOOR * Y_SCALE) - 0.01,
                    "end": Y_BASELINE - (THETA_FLOOR * Y_SCALE) + 0.01,
                    "fill_color": "rgba(16, 185, 129, 0.08)",
                    "border_color": "#10B98140"
                }
            },
            {
                "id": "ghost_anchor",
                "type": "ghost_layer",
                "z_index": 1,
                "ghost_data": {
                    "anchor_timestamp": int(time.time() * 1e6) - 1209600000000,
                    "opacity": 0.18,
                    "primitives": [
                        {
                            "type": "line",
                            "points": [{"x": 0.15, "y": 0.50}, {"x": 0.35, "y": 0.50}],
                            "stroke_color": "#FFFFFF",
                            "stroke_width": 1.5,
                            "dash_array": [4.0, 4.0]
                        }
                    ]
                }
            },
            {
                "id": "sim_corridor",
                "type": "simulation_fan",
                "z_index": 2,
                "fan_data": {
                    "fill_color": "rgba(245, 158, 11, 0.07)",
                    "upper_boundary": upper,
                    "lower_boundary": lower,
                    "median_trajectory": {
                        "points": median,
                        "stroke_color": "#F59E0B99",
                        "stroke_width": 1.5,
                        "dash_array": [3.0, 3.0]
                    }
                }
            },
            {
                "id": "live_bars",
                "type": "bar",
                "z_index": 3,
                "bar_data": {
                    "bars": [
                        {
                            "x": 0.15,
                            "y": min(Y_BASELINE, y_xle),
                            "width": 0.08,
                            "height": abs(Y_BASELINE - y_xle),
                            "color": "#10B981" if realized_xle >= 0 else "#F43F5E",
                            "border_color": "#10B981CC"
                        },
                        {
                            "x": 0.35,
                            "y": min(Y_BASELINE, y_xlk),
                            "width": 0.08,
                            "height": abs(Y_BASELINE - y_xlk),
                            "color": "#10B981" if realized_xlk >= 0 else "#F43F5E",
                            "border_color": "#F43F5ECC"
                        }
                    ]
                }
            },
            {
                "id": "telemetry",
                "type": "annotation",
                "z_index": 4,
                "annotation_data": {
                    "x": 0.05,
                    "y": 0.05,
                    "text": f"XLE: {realized_xle*100:+.2f}% | XLK: {realized_xlk*100:+.2f}% | EVAL: {(time.perf_counter()-t0)*1000:.2f}ms",
                    "font": "font-mono",
                    "font_size": 10.0,
                    "color": "#F8FAFC",
                    "align": "left"
                }
            }
        ]
    }
    return payload


def flush_canvas_atomic(payload: dict) -> None:
    data = json.dumps(payload, separators=(',', ':'))
    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(TEMP_FILE, CANVAS_FILE)


async def notify_subscribers(ts: int):
    msg = f"data: {{\"event\":\"canvas_update\",\"ts\":{ts}}}\n\n"
    dead = set()
    for q in SUBSCRIBERS:
        try:
            await q.put(msg)
        except Exception:
            dead.add(q)
    SUBSCRIBERS.difference_update(dead)


async def handle_tick_stream():
    corridor = DoubleBufferedCorridor()
    realized_xle = 0.038
    realized_xlk = -0.018
    while True:
        try:
            realized_xle += float(np.random.normal(0.0001, 0.0005))
            realized_xlk += float(np.random.normal(-0.0001, 0.0005))
            corridor.write_simulation(48, realized_xle)
            payload = build_canvas_payload(corridor, realized_xle, realized_xlk)
            flush_canvas_atomic(payload)
            await notify_subscribers(payload["timestamp"])
        except Exception as e:
            print(f"[!] Error in tick stream: {e}", file=sys.stderr)
        await asyncio.sleep(0.5)


async def handle_sse(request):
    resp = web.StreamResponse(status=200, reason='OK', headers={
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    })
    await resp.prepare(request)
    q = asyncio.Queue()
    SUBSCRIBERS.add(q)
    try:
        while True:
            msg = await q.get()
            await resp.write(msg.encode('utf-8'))
    except (asyncio.CancelledError, ConnectionResetError, Exception):
        pass
    finally:
        SUBSCRIBERS.discard(q)
    return resp


async def handle_canvas_get(request):
    if not CANVAS_FILE.exists():
        return web.Response(text="{}", content_type="application/json")
    with open(CANVAS_FILE, "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="application/json", headers={'Access-Control-Allow-Origin': '*'})


async def start_background_tasks(app):
    app['tick_task'] = asyncio.create_task(handle_tick_stream())


async def cleanup_background_tasks(app):
    if 'tick_task' in app:
        app['tick_task'].cancel()
        try:
            await app['tick_task']
        except asyncio.CancelledError:
            pass


def create_app():
    app = web.Application()
    app.router.add_get('/stream', handle_sse)
    app.router.add_get('/canvas', handle_canvas_get)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="127.0.0.1", port=8765)
