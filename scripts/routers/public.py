from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil
from datetime import datetime, timedelta, timezone
from core.db import DB_PATH, get_db
from core.security import (
    get_current_user, require_pilot, require_manager_or_pilot, security,
    _get_user_modules, _create_token,
)

router = APIRouter()



# ── Wild Paws Smyrna Heights Integration Endpoints ───────────────────────────
class RoomChatterRequest(BaseModel):
    room_id: str
    sender: str
    message: str

class ArtAuctionRequest(BaseModel):
    room_id: str
    title: str
    price: int
    has_frame: int = 0

@router.get("/api/public/room_chatter/{room_id}")
async def get_room_chatter(room_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT sys_id, room_id, sender, message, created_on FROM sys_room_chatter WHERE room_id=? ORDER BY created_on ASC", (room_id,)).fetchall()
    conn.close()
    return {"status": "success", "messages": [dict(r) for r in rows]}

@router.post("/api/public/room_chatter")
async def post_room_chatter(req: RoomChatterRequest):
    conn = sqlite3.connect(DB_PATH)
    sys_id = uuid.uuid4().hex
    conn.execute("INSERT INTO sys_room_chatter (sys_id, room_id, sender, message) VALUES (?, ?, ?, ?)",
                 (sys_id, req.room_id, req.sender, req.message))
    conn.commit()
    conn.close()
    return {"status": "success", "sys_id": sys_id}

@router.get("/api/public/art_auction")
async def get_art_auctions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT sys_id, room_id, title, status, has_frame, price, created_on FROM sys_art_auction ORDER BY created_on DESC").fetchall()
    conn.close()
    return {"status": "success", "auctions": [dict(r) for r in rows]}

@router.post("/api/public/art_auction/create")
async def create_art_auction(req: ArtAuctionRequest):
    conn = sqlite3.connect(DB_PATH)
    sys_id = uuid.uuid4().hex
    conn.execute("INSERT INTO sys_art_auction (sys_id, room_id, title, status, has_frame, price) VALUES (?, ?, ?, 'OPEN', ?, ?)",
                 (sys_id, req.room_id, req.title, req.has_frame, req.price))
    conn.commit()
    conn.close()
    return {"status": "success", "sys_id": sys_id}

@router.post("/api/public/art_auction/frame/{sys_id}")
async def frame_art_auction(sys_id: str):
    import random
    import glob
    import os
    
    # Locate raw frame images
    raw_images = glob.glob("/home/james/stacklabs/media_vault/frame_*.jpg")
    if raw_images:
        input_img = random.choice(raw_images)
        output_dir = "/home/james/stacklabs/media_vault/01_Assets/Inbox"
        os.makedirs(output_dir, exist_ok=True)
        output_img = os.path.join(output_dir, f"framed_{sys_id}.png")
        
        # Run jack_frames.py to overlay rustic wood border
        venv_python = "/home/james/stacklabs/.venv/bin/python3"
        script_path = "/home/james/stacklabs/scripts/jack_frames.py"
        try:
            subprocess.run([venv_python, script_path, input_img, output_img, "--border", "30"], check=True)
            print(f"Subprocess successfully framed image: {input_img} -> {output_img}")
        except Exception as e:
            print(f"Error executing jack_frames.py: {e}")
            
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE sys_art_auction SET has_frame=1 WHERE sys_id=?", (sys_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@router.post("/api/public/use_nap_mist")
async def use_nap_mist(req: dict):
    username = req.get("username", "barb")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT nap_mist_balance FROM sys_user WHERE user_name=?", (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    balance = row[0] or 0
    if balance <= 0:
        conn.close()
        return {"status": "failure", "message": "No Nap Mist remaining!"}
        
    new_balance = balance - 1
    c.execute("UPDATE sys_user SET nap_mist_balance=? WHERE user_name=?", (new_balance, username))
    
    # Log system message
    chatter_id = uuid.uuid4().hex
    c.execute("INSERT INTO sys_room_chatter (sys_id, room_id, sender, message) VALUES (?, 'smyrna_heights', 'system', ?)",
              (chatter_id, f"🌿 Nap Mist Activated by @{username}! Greta's quarantine audits muted for 30 minutes. Balance: {new_balance}"))
    conn.commit()
    conn.close()
    return {"status": "success", "balance": new_balance}
# ── End Wild Paws Smyrna Heights Integration Endpoints ───────────────────────

# ── StackLabs Public Gateway Settings ─────────────────────────────────────────
class StackLabsQuoteRequest(BaseModel):
    quote: str

@router.get("/api/public/stacklabs/quote")
async def get_stacklabs_quote():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM sys_user_preference WHERE user_name='global' AND name='stacklabs.gateway.quote'")
    row = c.fetchone()
    conn.close()
    if row:
        return {"status": "success", "quote": row[0]}
    # Default fallback quote
    default_quote = "The cloud is just someone else's expensive computer you can't touch. We mix our software like premium whiskey: local, pure, and barrel-aged on dedicated local hardware."
    return {"status": "success", "quote": default_quote}

@router.post("/api/public/stacklabs/quote")
async def set_stacklabs_quote(req: StackLabsQuoteRequest):
    conn = sqlite3.connect(DB_PATH)
    import uuid
    conn.execute("""
        INSERT INTO sys_user_preference (sys_id, user_name, name, value) 
        VALUES (?, 'global', 'stacklabs.gateway.quote', ?)
        ON CONFLICT(user_name, name) DO UPDATE SET value=excluded.value, sys_updated_on=CURRENT_TIMESTAMP
    """, (uuid.uuid4().hex, req.quote))
    conn.commit()
    conn.close()
    return {"status": "success", "quote": req.quote}

@router.get("/api/public/identify")
async def public_identify(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    real_ip = request.headers.get("x-real-ip")
    
    # Resolve actual IP from proxies
    ip = real_ip or (forwarded_for.split(",")[0].strip() if forwarded_for else client_ip)
    
    # Query database for all active users
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT user_name, role, display_name, active, tailscale_ip 
        FROM sys_user 
        WHERE active = 1
    """)
    rows = c.fetchall()
    conn.close()
    
    row = None
    for r in rows:
        db_ips = [x.strip() for x in (r["tailscale_ip"] or "").split(",") if x.strip()]
        if ip in db_ips:
            row = r
            break
            
    if row:
        user = dict(row)
        user_name = user["user_name"]
        
        # Limit auto-login to authorized users (james, dbarb, barb, eileen)
        allowed_users = {"james", "dbarb", "barb", "eileen"}
        if user_name.lower().strip() in allowed_users:
            modules = _get_user_modules(user_name)
            token = _create_token(user_name, user["role"] or "guest", user["display_name"] or user_name, modules)
            
            # Formulate greeting
            if user_name == "james":
                greeting = "WELCOME PILOT Carroll. High-density cockpit telemetry online. Focus matrix locked."
            elif user_name in ["dbarb", "barb"]:
                greeting = "Hello Barb. Smyrna heights rustic catalog ready. Let's roll."
            elif user_name == "eileen":
                greeting = "Eileen identified. Welcome back."
            else:
                greeting = f"Welcome back, {user['display_name'] or user_name}."
                
            # Assign outpost target port
            target_port = 3016
            if user_name == "james":
                target_port = 3016
            elif user_name in ["dbarb", "barb"]:
                target_port = 3020
            elif user_name == "eileen":
                target_port = 3017
                
            return {
                "status": "success",
                "identified": True,
                "token": token,
                "user_name": user_name,
                "display_name": user["display_name"] or user_name,
                "role": user["role"] or "guest",
                "modules": modules,
                "greeting": greeting,
                "avatar_url": f"/api/persona_image/{user_name}",
                "target_port": target_port
            }
            
    # Fallback to hardcoded mapping for sean, or default guest response
    mapping = {
        "100.88.5.122": {
            "user_name": "sean",
            "display_name": "Sean Carroll",
            "role": "guest",
            "greeting": "Sean Carroll identified. Hobbes laptop connection secure.",
            "avatar_url": "/api/persona_image/sean",
            "target_port": 3016
        }
    }
    
    if ip in mapping:
        user_name = mapping[ip]["user_name"]
        modules = _get_user_modules(user_name)
        token = _create_token(user_name, mapping[ip]["role"], mapping[ip]["display_name"], modules)
        return {
            "status": "success",
            "identified": True,
            "token": token,
            "modules": modules,
            **mapping[ip]
        }
        
    return {
        "status": "success", 
        "identified": False, 
        "ip": ip, 
        "user_name": "guest", 
        "display_name": "Tailnet Peer", 
        "role": "guest", 
        "greeting": "Authenticated Tailnet peer connection verified. Welcome to StackLabs.",
        "target_port": 3016
    }
# ── End StackLabs Public Gateway Settings ─────────────────────────────────────

@router.get("/api/public/stacks")
async def public_stacks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT name, port, status, short_description, icon FROM cmdb_ci_appl WHERE active = 1")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
