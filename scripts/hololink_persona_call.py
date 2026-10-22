#!/usr/bin/env python3
"""
hololink_persona_call.py
========================
ENHC0000044 — FanStack Hololink Persona Voice Call

Handles server-side WebRTC for live fan-to-persona audio sessions.
One fan at a time per persona (1-on-1 exclusive). Room-scoped persona.

Architecture:
  Fan browser (mic) → WebRTC offer → this server
  Server creates RTCPeerConnection with:
    - PersonaAvatarTrack (video): static persona image @ 30fps
    - PersonaVoiceTrack (audio): asyncio.Queue fed by STT→MARD→TTS pipeline
  Pipeline runs as asyncio task alongside the WebRTC session.

Routes (mounted by sovereign_core_api.py):
  POST /api/persona-call/offer    — WebRTC SDP offer
  POST /api/persona-call/ice      — ICE candidate
  POST /api/persona-call/hangup   — End session
  GET  /api/persona-call/status   — Active sessions (pilot only)
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Optional

import numpy as np
from fastapi import Request
from fastapi.responses import JSONResponse
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaBlackhole
import fractions

logger = logging.getLogger("persona_call")

SA_CREDENTIALS = "/home/james/stacklabs/config/vertex_sa.json"
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", SA_CREDENTIALS)

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
PERSONA_IMAGE_DIR = "/home/james/stacklabs/config/persona_avatars"
SESSION_TIMEOUT_SECS = 600  # 10 minutes max

# ── Room → Persona mapping ─────────────────────────────────────────────────────
ROOM_PERSONA_MAP = {
    "scruffys_tavern":   "barf",
    "the_press_box":     "wardy",
    "bullpen_sessions":  "scruffy",
    "hot_corner":        "barf",
    "default":           "barf",
}

# ── Active sessions: persona_name → session dict ───────────────────────────────
# Enforces 1-on-1: a persona can only be in one call at a time
active_sessions: dict[str, dict] = {}


# ── Video Track: Static persona avatar image ───────────────────────────────────
class PersonaAvatarTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, persona_name: str):
        super().__init__()
        self.persona_name = persona_name
        self._timestamp = 0
        self._frame_data = self._load_avatar(persona_name)

    def _load_avatar(self, persona_name: str) -> np.ndarray:
        """Load persona image → BGR numpy array. Fallback to solid color."""
        img_path = os.path.join(PERSONA_IMAGE_DIR, f"{persona_name}.jpg")
        try:
            import cv2
            if os.path.exists(img_path):
                frame = cv2.imread(img_path)
                return cv2.resize(frame, (640, 480))
        except ImportError:
            pass
        # Fallback: Mets orange solid frame (255, 89, 16 in BGR)
        return np.full((480, 640, 3), [16, 89, 255], dtype=np.uint8)

    async def recv(self):
        from aiortc.mediastreams import VIDEO_TIME_BASE, VIDEO_CLOCK_RATE
        from av import VideoFrame

        pts = self._timestamp
        self._timestamp += int(VIDEO_CLOCK_RATE / 30)  # 30fps

        frame = VideoFrame.from_ndarray(self._frame_data, format="bgr24")
        frame.pts = pts
        frame.time_base = fractions.Fraction(1, VIDEO_CLOCK_RATE)

        # Throttle to 30fps
        await asyncio.sleep(1 / 30)
        return frame


# ── Audio Track: Queue-fed persona voice ──────────────────────────────────────
class PersonaVoiceTrack(MediaStreamTrack):
    kind = "audio"
    SAMPLE_RATE = 48000
    SAMPLES_PER_FRAME = 960  # 20ms at 48kHz

    def __init__(self):
        super().__init__()
        self.audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=10)
        self._timestamp = 0
        self._buffer = b""

    async def recv(self):
        from av import AudioFrame

        target_bytes = self.SAMPLES_PER_FRAME * 2  # 16-bit = 2 bytes/sample

        # Drain queue into buffer until we have enough for one frame
        while len(self._buffer) < target_bytes:
            try:
                chunk = self.audio_queue.get_nowait()
                self._buffer += chunk
            except asyncio.QueueEmpty:
                # Serve silence while waiting for TTS
                self._buffer += b"\x00" * (target_bytes - len(self._buffer))

        frame_data = self._buffer[:target_bytes]
        self._buffer = self._buffer[target_bytes:]

        # Build AudioFrame
        audio_array = np.frombuffer(frame_data, dtype=np.int16).reshape(1, -1)
        frame = AudioFrame.from_ndarray(audio_array, format="s16", layout="mono")
        frame.sample_rate = self.SAMPLE_RATE
        frame.pts = self._timestamp
        frame.time_base = fractions.Fraction(1, self.SAMPLE_RATE)
        self._timestamp += self.SAMPLES_PER_FRAME

        await asyncio.sleep(0.02)  # ~20ms cadence
        return frame


# ── Session management ────────────────────────────────────────────────────────
def get_persona_for_room(room_id: str) -> str:
    return ROOM_PERSONA_MAP.get(room_id, ROOM_PERSONA_MAP["default"])


def is_persona_busy(persona_name: str) -> bool:
    return persona_name in active_sessions


def register_session(session_id: str, persona_name: str, room_id: str,
                     pc: RTCPeerConnection, voice_track: PersonaVoiceTrack,
                     pipeline_task: asyncio.Task) -> dict:
    session = {
        "session_id": session_id,
        "persona_name": persona_name,
        "room_id": room_id,
        "pc": pc,
        "voice_track": voice_track,
        "pipeline_task": pipeline_task,
        "started_at": time.time(),
        "transcript": [],
    }
    active_sessions[persona_name] = session
    logger.info(f"[CALL] Session {session_id} started — {persona_name} in {room_id}")
    return session


async def teardown_session(persona_name: str, reason: str = "hangup"):
    session = active_sessions.pop(persona_name, None)
    if not session:
        return
    session_id = session["session_id"]
    logger.info(f"[CALL] Session {session_id} ending — reason: {reason}")

    if not session["pipeline_task"].done():
        session["pipeline_task"].cancel()

    try:
        await session["pc"].close()
    except Exception:
        pass

    logger.info(f"[CALL] Session {session_id} closed cleanly")


# ── Route Handlers ────────────────────────────────────────────────────────────
async def handle_offer(request: Request) -> JSONResponse:
    """
    POST /api/persona-call/offer
    Body: { "sdp": "...", "type": "offer", "room_id": "scruffys_tavern", "fan_id": "..." }
    """
    from scripts.persona_voice_pipeline import run_pipeline

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    room_id = body.get("room_id", "default")
    fan_id = body.get("fan_id", "anonymous")
    persona_name = get_persona_for_room(room_id)

    # Enforce 1-on-1
    if is_persona_busy(persona_name):
        busy_session = active_sessions[persona_name]
        elapsed = int(time.time() - busy_session["started_at"])
        return JSONResponse({
            "error": "busy",
            "message": f"{persona_name.capitalize()} is on a call right now 🍺",
            "elapsed_seconds": elapsed
        }, status_code=409)

    # Create WebRTC peer connection
    pc = RTCPeerConnection()
    voice_track = PersonaVoiceTrack()
    avatar_track = PersonaAvatarTrack(persona_name)
    session_id = str(uuid.uuid4())

    pc.addTrack(voice_track)
    pc.addTrack(avatar_track)

    # Accept incoming audio from fan (pipe to STT)
    fan_audio_track_holder = {"track": None}

    @pc.on("track")
    def on_track(track: MediaStreamTrack):
        if track.kind == "audio":
            fan_audio_track_holder["track"] = track
            logger.info(f"[CALL] {session_id} — fan audio track received")

    # Set remote description (fan's offer)
    await pc.setRemoteDescription(RTCSessionDescription(
        sdp=body.get("sdp", ""),
        type=body.get("type", "offer")
    ))

    # Create answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Start STT→LLM→TTS pipeline as background task
    pipeline_task = asyncio.create_task(
        run_pipeline(
            session_id=session_id,
            persona_name=persona_name,
            room_id=room_id,
            fan_id=fan_id,
            fan_audio_track_holder=fan_audio_track_holder,
            voice_queue=voice_track.audio_queue,
        )
    )

    # Session timeout watchdog
    async def watchdog():
        await asyncio.sleep(SESSION_TIMEOUT_SECS)
        if persona_name in active_sessions:
            logger.warning(f"[CALL] Session {session_id} timed out after {SESSION_TIMEOUT_SECS}s")
            await teardown_session(persona_name, reason="timeout")

    asyncio.create_task(watchdog())

    register_session(session_id, persona_name, room_id, pc, voice_track, pipeline_task)

    return JSONResponse({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
        "session_id": session_id,
        "persona": persona_name,
    })


async def handle_ice(request: Request) -> JSONResponse:
    """
    POST /api/persona-call/ice
    Body: { "session_id": "...", "candidate": {...} }
    """
    from aiortc import RTCIceCandidate

    body = await request.json()
    session_id = body.get("session_id")

    # Find session by session_id
    session = next(
        (s for s in active_sessions.values() if s["session_id"] == session_id),
        None
    )
    if not session:
        return JSONResponse({"error": "session not found"}, status_code=404)

    cand_data = body.get("candidate", {})
    if cand_data:
        candidate = RTCIceCandidate(
            component=cand_data.get("component", 1),
            foundation=cand_data.get("foundation", ""),
            ip=cand_data.get("ip", ""),
            port=cand_data.get("port", 0),
            priority=cand_data.get("priority", 0),
            protocol=cand_data.get("protocol", "udp"),
            type=cand_data.get("type", "host"),
            sdpMid=cand_data.get("sdpMid"),
            sdpMLineIndex=cand_data.get("sdpMLineIndex"),
        )
        await session["pc"].addIceCandidate(candidate)

    return JSONResponse({"status": "ok"})


async def handle_hangup(request: Request) -> JSONResponse:
    """
    POST /api/persona-call/hangup
    Body: { "session_id": "..." } OR { "persona": "barf" }
    """
    body = await request.json()
    session_id = body.get("session_id")
    persona_name = body.get("persona")

    if session_id:
        session = next(
            (s for s in active_sessions.values() if s["session_id"] == session_id),
            None
        )
        if session:
            persona_name = session["persona_name"]

    if persona_name and persona_name in active_sessions:
        await teardown_session(persona_name, reason="hangup")
        return JSONResponse({"status": "ended"})

    return JSONResponse({"status": "no active session"}, status_code=404)


async def handle_status(request: Request) -> JSONResponse:
    """GET /api/persona-call/status — active sessions overview"""
    now = time.time()
    result = {}
    for persona_name, session in active_sessions.items():
        result[persona_name] = {
            "session_id": session["session_id"],
            "room_id": session["room_id"],
            "duration_seconds": int(now - session["started_at"]),
            "transcript_turns": len(session["transcript"]),
        }
    return JSONResponse({"active_calls": result, "count": len(result)})


# Routes are mounted by sovereign_core_api.py via fastapi_app.add_api_route()
# See: hololink_persona_call import block in sovereign_core_api.py

