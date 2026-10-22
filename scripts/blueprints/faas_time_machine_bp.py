#!/home/james/stacklabs/.venv/bin/python3
"""
FastAPI Blueprint for FaaS Stream Sniper Time-Machine Scrub Bar & Reverse Lookup (WO0011280).
Mounts:
- GET /api/snipe/{snipe_id}/time_machine
- GET /api/snipe/{snipe_id}/rewind?t={timestamp}&q={phrase}
- GET /api/snipe/{snipe_id}/audio
- GET /api/discord/circuit_breaker/status
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

ROOT_DIR = Path("/home/james/stacklabs")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.compile_snipe_time_machine import (
    DATA_SNIPES_DIR,
    VFS_SNIPES_DIR,
    compile_cartridge_for_snipe,
)
from scripts.discord_auth_circuit_breaker import DiscordAuthCircuitBreaker, LOCK_FILE

logger = logging.getLogger("faas_time_machine_bp")
router = APIRouter(tags=["faas_time_machine"])

SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{2,64}$")


def _validate_snipe_id(snipe_id: str) -> str:
    cleaned = snipe_id.strip()
    if not SAFE_ID_RE.match(cleaned):
        raise HTTPException(status_code=400, detail="Invalid snipe_id format.")
    return cleaned


def _load_or_compile_cartridge(snipe_id: str, force_rebuild: bool = False) -> Dict[str, Any]:
    sid = _validate_snipe_id(snipe_id)
    if not force_rebuild:
        for base in (VFS_SNIPES_DIR, DATA_SNIPES_DIR):
            candidate = base / sid / "time_machine.json"
            if candidate.exists():
                try:
                    return json.loads(candidate.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    logger.warning("Recompiling corrupted time_machine.json for %s: %s", sid, exc)
    return compile_cartridge_for_snipe(sid)


def _parse_timestamp_to_seconds(raw_t: str) -> float:
    cleaned = raw_t.strip()
    if not cleaned:
        return 0.0
    if ":" in cleaned:
        parts = [p.strip() for p in cleaned.split(":")]
        try:
            if len(parts) == 3:
                return float(int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2]))
            if len(parts) == 2:
                return float(int(parts[0]) * 60 + float(parts[1]))
        except ValueError:
            return 0.0
    try:
        return max(0.0, float(cleaned))
    except ValueError:
        return 0.0


@router.get("/api/snipe/{snipe_id}/time_machine")
def get_snipe_time_machine(
    snipe_id: str,
    rebuild: bool = Query(default=False, description="Force recompile from SQLite WAL and Whisper segments."),
) -> Dict[str, Any]:
    return _load_or_compile_cartridge(snipe_id, force_rebuild=rebuild)


@router.api_route("/api/snipe/{snipe_id}/audio", methods=["GET", "HEAD"])
def get_snipe_audio_stream(snipe_id: str):
    sid = _validate_snipe_id(snipe_id)
    for base in (VFS_SNIPES_DIR, DATA_SNIPES_DIR):
        audio_file = base / sid / "audio.m4a"
        if audio_file.exists():
            return FileResponse(
                path=str(audio_file),
                media_type="audio/mp4",
                filename=f"audio_{sid}.m4a",
                headers={"Accept-Ranges": "bytes"},
            )
    raise HTTPException(status_code=404, detail=f"Audio not found for snipe: {sid}")


@router.get("/api/snipe/{snipe_id}/rewind")
def rewind_snipe_time_machine(
    snipe_id: str,
    t: Optional[str] = Query(default=None, description="Target audio timestamp in seconds or MM:SS / HH:MM:SS."),
    q: Optional[str] = Query(default=None, description="Spoken phrase or chat keyword to jump to."),
    window: float = Query(default=45.0, ge=10.0, le=300.0, description="Causal window in seconds."),
) -> Dict[str, Any]:
    cartridge = _load_or_compile_cartridge(snipe_id, force_rebuild=False)
    segments: List[Dict[str, Any]] = cartridge.get("segments", [])
    buckets: List[Dict[str, Any]] = cartridge.get("buckets", [])
    hls_lag = float(cartridge.get("hls_lag_seconds", 14.2))
    bucket_size = float(cartridge.get("bucket_size_seconds", 10.0))

    target_sec = _parse_timestamp_to_seconds(t) if t else 0.0
    matched_phrase_hits: List[Dict[str, Any]] = []

    if q and q.strip():
        needle = q.strip().lower()
        for seg in segments:
            if needle in str(seg.get("text", "")).lower():
                matched_phrase_hits.append({
                    "source": "WHISPER_AUDIO",
                    "offset_sec": seg["start_sec"],
                    "timestamp_label": f"{int(seg['start_sec'] // 60):02d}:{int(seg['start_sec'] % 60):02d}",
                    "text": seg["text"],
                })
        for b in buckets:
            for msg in b.get("top_messages", []):
                if needle in str(msg.get("message", "")).lower() or needle in str(msg.get("author", "")).lower():
                    matched_phrase_hits.append({
                        "source": "BLEACHER_CHAT",
                        "offset_sec": b["offset_sec"],
                        "timestamp_label": f"{int(b['offset_sec'] // 60):02d}:{int(b['offset_sec'] % 60):02d}",
                        "author": msg.get("author"),
                        "text": msg.get("message"),
                    })
        if matched_phrase_hits and not t:
            target_sec = float(matched_phrase_hits[0]["offset_sec"])

    half_w = window / 2.0
    win_start = max(0.0, target_sec - 10.0)
    win_end = target_sec + max(20.0, half_w)

    window_segments = [
        seg for seg in segments if seg["end_sec"] >= win_start and seg["start_sec"] <= win_end
    ]
    window_buckets = [
        b for b in buckets if (b["offset_sec"] + bucket_size) >= win_start and b["offset_sec"] <= win_end
    ]
    window_messages: List[Dict[str, Any]] = []
    for b in window_buckets:
        window_messages.extend(b.get("top_messages", []))

    return {
        "snipe_id": cartridge["snipe_id"],
        "target_audio_sec": round(target_sec, 2),
        "compensated_chat_sec": round(target_sec + hls_lag, 2),
        "hls_lag_seconds": hls_lag,
        "query_phrase": q or "",
        "phrase_hits": matched_phrase_hits[:25],
        "whisper_window": window_segments[:40],
        "chat_reaction_window": window_messages[:50],
    }


@router.get("/api/discord/circuit_breaker/status")
def get_discord_circuit_breaker_status() -> Dict[str, Any]:
    breaker = DiscordAuthCircuitBreaker()
    if LOCK_FILE.exists():
        try:
            return json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"breaker_state": "TRIPPED", "lock_file": str(LOCK_FILE)}
    return {"breaker_state": "CLOSED", "tripped": breaker.is_tripped(), "lock_file": str(LOCK_FILE)}
