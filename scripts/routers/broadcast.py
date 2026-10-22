"""
Sovereign OS: Broadcast Network REST Router
Path: /home/james/stacklabs/scripts/routers/broadcast.py
Authority: James Carroll (Pilot / Lead Systems Architect)
SDLC: STRY0010012-BLUNDERDOME-MARD-AUTONOMOUS-BROADCAST-NETWORK

Provides REST endpoints for:
- Show discovery (The Blunderdome, The Skew, AetherVet)
- Episode management and timecoded transcript playback
- Audio streaming for master episode MP3s
- Dynamic seat roster broadcast generation via MARD Audio Engine
- Environmental DSP preset catalog
"""

import os
import sys
import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Dynamic path resolution
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in [REPO_ROOT, SCRIPTS_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.db import get_db
from core.broadcast_audio_engine import DSP_REGISTRY, generate_episode_pipeline

router = APIRouter(prefix="/api/broadcast", tags=["Broadcast Network"])
logger = logging.getLogger("BroadcastRouter")


# ── Pydantic Request Models ───────────────────────────────────────────────────

class SeatConfig(BaseModel):
    seat: int = Field(default=0, description="Seat index (0..N)")
    role: str = Field(default="caller", description="Role: host | caller | analyst | color_commentator")
    persona_id: str = Field(..., description="Persona ID or handle (e.g. 'sal', 'barf', '7_train')")
    dsp_preset: Optional[str] = Field(default="telephone", description="DSP filter preset key")


class GenerateBroadcastRequest(BaseModel):
    show_id: str = Field(default="show_blunderdome", description="Show ID")
    title: str = Field(..., description="Episode title")
    topic: str = Field(..., description="Broadcast discussion topic / trigger")
    seat_roster: List[SeatConfig] = Field(..., description="Dynamic seating configuration")
    trigger_context: Optional[str] = Field(default="", description="Optional Statcast / game telemetry context")
    game_pk: Optional[str] = Field(default=None, description="Optional associated Game PK")


# ── REST Endpoints ─────────────────────────────────────────────────────────────

@router.get("/shows")
async def list_shows():
    """Retrieve all registered broadcast shows / stations."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sys_broadcast_show ORDER BY created_at ASC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/shows/{show_id}")
async def get_show(show_id: str):
    """Retrieve details for a specific broadcast show."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sys_broadcast_show WHERE id = ?", (show_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Show '{show_id}' not found.")
        return dict(row)


@router.get("/episodes")
async def list_episodes(show_id: Optional[str] = None, limit: int = 50):
    """List broadcast episodes with optional show filtering."""
    with get_db() as conn:
        cursor = conn.cursor()
        if show_id:
            cursor.execute(
                "SELECT * FROM sys_broadcast_episode WHERE show_id = ? ORDER BY created_at DESC LIMIT ?",
                (show_id, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM sys_broadcast_episode ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        rows = cursor.fetchall()
        
        episodes = []
        for r in rows:
            ep_dict = dict(r)
            if ep_dict.get("metadata_json"):
                try:
                    ep_dict["metadata"] = json.loads(ep_dict["metadata_json"])
                except Exception:
                    ep_dict["metadata"] = {}
            episodes.append(ep_dict)
        return episodes


@router.get("/episodes/{episode_id}")
async def get_episode_details(episode_id: str):
    """Retrieve complete episode details along with timecoded dialogue segments."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sys_broadcast_episode WHERE id = ?", (episode_id,))
        ep_row = cursor.fetchone()
        if not ep_row:
            raise HTTPException(status_code=404, detail=f"Episode '{episode_id}' not found.")
        
        ep_dict = dict(ep_row)
        if ep_dict.get("metadata_json"):
            try:
                ep_dict["metadata"] = json.loads(ep_dict["metadata_json"])
            except Exception:
                ep_dict["metadata"] = {}

        cursor.execute(
            "SELECT * FROM sys_broadcast_segment WHERE episode_id = ? ORDER BY segment_index ASC",
            (episode_id,)
        )
        seg_rows = cursor.fetchall()
        ep_dict["segments"] = [dict(s) for s in seg_rows]
        return ep_dict


@router.api_route("/episodes/{episode_id}/audio", methods=["GET", "HEAD"])
async def stream_episode_audio(episode_id: str):
    """Stream or download the rendered master MP3 audio file for an episode."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT audio_path, title FROM sys_broadcast_episode WHERE id = ?", (episode_id,))
        row = cursor.fetchone()
        if not row or not row["audio_path"] or not os.path.exists(row["audio_path"]):
            raise HTTPException(status_code=404, detail="Audio file not found or not yet generated.")
        
        return FileResponse(
            path=row["audio_path"],
            media_type="audio/mpeg",
            filename=f"{episode_id}.mp3"
        )


@router.get("/presets/dsp")
async def get_dsp_presets():
    """List available environmental DSP presets in the system."""
    presets = []
    for key, data in DSP_REGISTRY.items():
        presets.append({
            "key": key,
            "name": data.get("name", key),
            "description": data.get("description", ""),
            "highpass_hz": data.get("highpass_hz"),
            "lowpass_hz": data.get("lowpass_hz"),
            "compression_ratio": data.get("compression_ratio"),
            "volume_multiplier": data.get("volume_multiplier"),
            "has_ambient": bool(data.get("ambient_file"))
        })
    return presets


@router.post("/generate")
async def generate_episode(request: GenerateBroadcastRequest):
    """
    Generate a new autonomous broadcast episode using dynamic seating and MARD audio engine.
    """
    try:
        seat_roster_dicts = [s.model_dump() for s in request.seat_roster]
        result = generate_episode_pipeline(
            show_id=request.show_id,
            title=request.title,
            topic=request.topic,
            seat_roster=seat_roster_dicts,
            trigger_context=request.trigger_context or "",
            game_pk=request.game_pk
        )
        return {
            "status": "success",
            "message": f"Broadcast episode '{request.title}' successfully generated.",
            "episode": result
        }
    except Exception as e:
        logger.error(f"Failed to generate broadcast episode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
