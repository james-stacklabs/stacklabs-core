#!/usr/bin/env python3
"""
scripts/routers/vector6_chat.py
===============================
Multi-channel Direct Wire Terminal IM backend for StackLabs Horizon Edge.
Enforces physical file-level channel isolation and passphrase security clearance.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Query, Body, Response
from fastapi.responses import FileResponse, JSONResponse
import logging
from pydantic import BaseModel

logger = logging.getLogger("vector6_chat")

try:
    from scripts.pilot_notifier import dispatch_pilot_alert
except ImportError:
    from pilot_notifier import dispatch_pilot_alert

router = APIRouter(tags=["Vector6Chat"])

STACKLABS_ROOT = Path("/home/james/stacklabs")
DATA_DIR = STACKLABS_ROOT / "data"
WIRES_DIR = DATA_DIR / "wires"
VOICE_DROPS_DIR = STACKLABS_ROOT / "pilot_drops" / "voice_drops"
HTML_CHAT_PATH = STACKLABS_ROOT / "apps" / "horizon_scratchpad" / "chat.html"
HORIZON_PASSPHRASE = "lfgm2027"

WIRES_DIR.mkdir(parents=True, exist_ok=True)
VOICE_DROPS_DIR.mkdir(parents=True, exist_ok=True)


class SendMessageRequest(BaseModel):
    channel: Optional[str] = "pawel"
    sender: str
    body: str
    type: Optional[str] = "text"
    display_name: Optional[str] = None
    audio_url: Optional[str] = None
    duration_sec: Optional[float] = 0.0


class ClearWireRequest(BaseModel):
    channel: Optional[str] = "pawel"


class AuthRequest(BaseModel):
    passphrase: str


def _check_wire_auth(request: Request) -> bool:
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host", "")).lower()

    # 1. Check header
    token = request.headers.get("x-wire-auth") or request.headers.get("authorization", "")
    if token.startswith("Bearer "):
        token = token[7:].strip()

    # 2. Check cookie
    if not token:
        token = request.cookies.get("wire_auth", "")

    # 3. Check query param
    if not token:
        token = request.query_params.get("auth", "")

    if token == HORIZON_PASSPHRASE:
        return True

    # If traffic is over public Cloudflare Tunnel, strictly require passphrase
    if "stacklabsllc.com" in host or host.startswith("chat.") or host.startswith("v6."):
        return False

    # Local loopback / internal mesh fallback
    client_host = request.client.host if request.client else ""
    if client_host in ["127.0.0.1", "::1"]:
        return True

    return False


def _enforce_public_firewall(request: Request, channel: Optional[str]):
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host", "")).lower()
    clean_chan = (channel or "pawel").lower().strip()
    if clean_chan == "barb" and "stacklabsllc.com" in host:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Barbara channel is restricted to internal mesh nodes."
        )
    if "stacklabsllc.com" in host or host.startswith("chat.") or host.startswith("v6."):
        if not _check_wire_auth(request):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Direct wire clearance passphrase required."
            )


def _get_wire_path(channel: str) -> Path:
    clean_chan = (channel or "pawel").lower().strip()
    if clean_chan not in ["pawel", "barb"]:
        clean_chan = "pawel"
    return WIRES_DIR / f"{clean_chan}.json"


def _load_wire_data(channel: str) -> dict:
    wire_path = _get_wire_path(channel)
    clean_chan = wire_path.stem
    display_title = "JAMES ⇄ PAWEL" if clean_chan == "pawel" else "JAMES ⇄ BARBARA"

    if not wire_path.exists():
        default_payload = {
            "channel_id": clean_chan,
            "display_title": display_title,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT"),
            "epoch_heartbeat": int(time.time()),
            "messages": []
        }
        _save_wire_data(clean_chan, default_payload)
        return default_payload

    try:
        content = wire_path.read_text(encoding="utf-8")
        return json.loads(content)
    except Exception:
        return {
            "channel_id": clean_chan,
            "display_title": display_title,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT"),
            "epoch_heartbeat": int(time.time()),
            "messages": []
        }


def _save_wire_data(channel: str, data: dict) -> None:
    wire_path = _get_wire_path(channel)
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT")
    data["epoch_heartbeat"] = int(time.time())
    temp_path = wire_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp_path, wire_path)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/api/v6/chat/auth")
def authenticate_wire(request: Request, body: AuthRequest):
    if body.passphrase == HORIZON_PASSPHRASE:
        resp = JSONResponse({"status": "AUTHENTICATED", "token": HORIZON_PASSPHRASE})
        resp.set_cookie(
            key="wire_auth",
            value=HORIZON_PASSPHRASE,
            max_age=86400 * 7,
            httponly=False,
            samesite="lax"
        )
        return resp
    raise HTTPException(status_code=401, detail="Invalid clearance passphrase")


@router.get("/api/v6/chat/messages")
@router.head("/api/v6/chat/messages")
@router.get("/api/v6/wire.json")
def get_wire_messages(request: Request, channel: str = Query("pawel"), limit: int = 100):
    _enforce_public_firewall(request, channel)
    data = _load_wire_data(channel)
    messages = data.get("messages", [])
    if limit > 0:
        messages = messages[-limit:]

    return JSONResponse({
        "status": "ONLINE",
        "channel_id": data.get("channel_id", channel),
        "display_title": data.get("display_title"),
        "updated_at": data.get("updated_at"),
        "epoch_heartbeat": data.get("epoch_heartbeat"),
        "message_count": len(messages),
        "messages": messages
    })


@router.post("/api/v6/chat/send")
def send_wire_message(request: Request, req: SendMessageRequest):
    _enforce_public_firewall(request, req.channel)
    channel_clean = (req.channel or "pawel").lower().strip()
    if channel_clean not in ["pawel", "barb"]:
        channel_clean = "pawel"

    sender_clean = req.sender.lower().strip()
    if sender_clean not in ["james", "pawel", "barb"]:
        sender_clean = "james"

    if req.display_name:
        display_name = req.display_name
    elif sender_clean == "james":
        display_name = "James Carroll"
    elif sender_clean == "barb":
        display_name = "Barbara"
    else:
        display_name = "Pawel Rudnicki"

    now_ts = datetime.now().strftime("%H:%M:%S")
    msg_id = f"msg_{int(time.time() * 1000)}"

    new_msg = {
        "id": msg_id,
        "timestamp": now_ts,
        "channel": channel_clean,
        "sender": sender_clean,
        "display_name": display_name,
        "type": req.type or "text",
        "body": req.body,
        "audio_url": req.audio_url,
        "duration_sec": req.duration_sec or 0.0,
        "verified_on_metal": True
    }

    data = _load_wire_data(channel_clean)
    data.setdefault("messages", []).append(new_msg)

    # Cap total memory length at 250 messages per channel
    if len(data["messages"]) > 250:
        data["messages"] = data["messages"][-250:]

    _save_wire_data(channel_clean, data)

    # Pilot Alert Trigger
    if sender_clean != "james":
        dispatch_pilot_alert(
            title=f"💬 [DIRECT WIRE] Message from {display_name}",
            body=f"Channel: #{channel_clean}\n\"{req.body}\"",
            priority="urgent",
            tags="speech_balloon,bell",
            click_url=f"https://listen.stacklabsllc.com/{channel_clean}"
        )

    return JSONResponse({"status": "DELIVERED", "channel": channel_clean, "message": new_msg})


@router.post("/api/v6/chat/clear")
def clear_wire_messages(
    request: Request,
    req: Optional[ClearWireRequest] = Body(None),
    channel: Optional[str] = Query(None)
):
    target = "pawel"
    if req and req.channel:
        target = req.channel
    elif channel:
        target = channel
    _enforce_public_firewall(request, target)
    channel_clean = (target or "pawel").lower().strip()
    if channel_clean not in ["pawel", "barb"]:
        channel_clean = "pawel"
    data = _load_wire_data(channel_clean)
    data["messages"] = []
    _save_wire_data(channel_clean, data)
    return JSONResponse({"status": "CLEARED", "channel": channel_clean})


@router.post("/api/v6/chat/voice_drop")
async def upload_voice_drop(
    request: Request,
    file: UploadFile = File(...),
    channel: str = Form("pawel"),
    sender: str = Form("pawel"),
    transcript: Optional[str] = Form(""),
    duration_sec: Optional[float] = Form(0.0)
):
    _enforce_public_firewall(request, channel)
    channel_clean = channel.lower().strip()
    if channel_clean not in ["pawel", "barb"]:
        channel_clean = "pawel"

    sender_clean = sender.lower().strip()
    if sender_clean not in ["james", "pawel", "barb"]:
        sender_clean = "pawel"

    filename = f"DROP_{int(time.time())}_{sender_clean}.webm"
    dest_path = VOICE_DROPS_DIR / filename

    content = await file.read()
    dest_path.write_bytes(content)

    audio_url = f"/api/v6/voice/{filename}"
    display_name = "James Carroll" if sender_clean == "james" else ("Barbara" if sender_clean == "barb" else "Pawel Rudnicki")
    now_ts = datetime.now().strftime("%H:%M:%S")
    msg_id = f"msg_{int(time.time() * 1000)}"

    new_msg = {
        "id": msg_id,
        "timestamp": now_ts,
        "channel": channel_clean,
        "sender": sender_clean,
        "display_name": display_name,
        "type": "voice_drop",
        "body": transcript or f"Voice drop received ({len(content)} bytes)",
        "audio_url": audio_url,
        "duration_sec": duration_sec or 0.0,
        "verified_on_metal": True
    }

    data = _load_wire_data(channel_clean)
    data.setdefault("messages", []).append(new_msg)
    _save_wire_data(channel_clean, data)

    # Pilot Alert Trigger
    if sender_clean != "james":
        dispatch_pilot_alert(
            title=f"🎙️ [VOICE DROP] New Audio Memo from {display_name}",
            body=f"Channel: #{channel_clean} | Duration: {duration_sec or 0.0:.1f}s | File: {filename}\n{transcript or 'Audio file stored on metal'}",
            priority="urgent",
            tags="microphone,rotating_light",
            click_url=f"https://listen.stacklabsllc.com{audio_url}"
        )

    # Trigger autonomous background transcription & dossier drafting
    import subprocess
    try:
        subprocess.Popen(
            [
                "/home/james/stacklabs/.venv/bin/python3",
                "/home/james/stacklabs/scripts/transcribe_voice_drop.py",
                str(dest_path)
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        logger.warning(f"Failed to spawn background transcription: {e}")

    return JSONResponse({"status": "UPLOADED", "channel": channel_clean, "message": new_msg})


@router.get("/api/v6/voice/{filename}")
@router.head("/api/v6/voice/{filename}")
def stream_voice_audio(filename: str):
    file_path = VOICE_DROPS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/webm")


@router.get("/v6/chat")
@router.head("/v6/chat")
@router.get("/cockpit/chat")
@router.head("/cockpit/chat")
@router.get("/barb")
@router.head("/barb")
@router.get("/v6/barb")
@router.head("/v6/barb")
@router.get("/pawel")
@router.head("/pawel")
@router.get("/v6/pawel")
@router.head("/v6/pawel")
def get_terminal_chat_view(request: Request, channel: Optional[str] = Query(None)):
    path = request.url.path.lower()
    target_channel = channel
    if not target_channel:
        if "barb" in path:
            target_channel = "barb"
        elif "pawel" in path:
            target_channel = "pawel"
    if target_channel == "barb":
        host = (request.headers.get("x-forwarded-host") or request.headers.get("host", "")).lower()
        if "stacklabsllc.com" in host:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Barbara channel is restricted to internal mesh nodes."
            )
    if HTML_CHAT_PATH.exists():
        return FileResponse(HTML_CHAT_PATH, media_type="text/html")
    return JSONResponse({"error": "Terminal chat view not found"}, status_code=404)


HTML_PASSPORT_PATH = STACKLABS_ROOT / "apps" / "horizon_scratchpad" / "passport.html"


@router.get("/passport")
@router.head("/passport")
@router.get("/pilot/passport")
@router.head("/pilot/passport")
def get_pilot_passport_view():
    if HTML_PASSPORT_PATH.exists():
        return FileResponse(HTML_PASSPORT_PATH, media_type="text/html")
    return JSONResponse({"error": "Pilot passport view not found"}, status_code=404)
