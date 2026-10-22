"""
Audio Media Stream Blueprint for Synapse Bus
Path: /home/james/stacklabs/scripts/blueprints/audio_bp.py
Mounted at /audio on Port 8088.
Serves static audio briefings securely behind Tailscale TLS.
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()
AUDIO_FILE = Path("/home/james/stacklabs/audio/daily_sprint.mp3")

@router.api_route("/daily_sprint.mp3", methods=["GET", "HEAD"])
@router.api_route("/daily", methods=["GET", "HEAD"])
async def get_daily_sprint_audio():
    """Streams the latest compiled daily sprint audio MP3."""
    if not AUDIO_FILE.exists():
        raise HTTPException(status_code=404, detail="Daily sprint audio not yet generated.")
    return FileResponse(
        path=str(AUDIO_FILE),
        media_type="audio/mpeg",
        filename="daily_sprint.mp3"
    )
