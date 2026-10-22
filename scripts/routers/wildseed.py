from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil
from datetime import datetime, timedelta, timezone
from core.db import DB_PATH, get_db
from core.security import get_current_user, require_pilot, require_manager_or_pilot, security

router = APIRouter()


# ── WildSeed Manufacturing OS (Type 6) Endpoints ──────────────────────────────

@router.get("/api/wildseed/dashboard")
async def ws_dashboard():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        batches_in_flight = conn.execute(
            "SELECT COUNT(*) as c FROM ws_batch WHERE status='IN_PROCESS'"
        ).fetchone()["c"]
        units_pending = conn.execute(
            "SELECT COALESCE(SUM(units_pending_lab),0) as c FROM ws_inventory"
        ).fetchone()["c"]
        compliance_flags = conn.execute(
            "SELECT COUNT(*) as c FROM ws_coa WHERE status='FAIL'"
        ).fetchone()["c"]
        recent_logs = conn.execute(
            "SELECT * FROM ws_compliance_log ORDER BY sys_created_on DESC LIMIT 5"
        ).fetchall()
        return {
            "batches_in_flight": batches_in_flight,
            "units_pending_lab_release": units_pending,
            "compliance_flags": compliance_flags,
            "recent_activity": [dict(r) for r in recent_logs]
        }
    finally:
        conn.close()

@router.get("/api/wildseed/batches")
async def ws_batches():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM ws_batch ORDER BY batch_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.get("/api/wildseed/batches/{batch_number}")
async def ws_batch_detail(batch_number: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        batch = conn.execute(
            "SELECT * FROM ws_batch WHERE batch_number=?", (batch_number,)
        ).fetchone()
        coa = conn.execute(
            "SELECT * FROM ws_coa WHERE batch_number=? ORDER BY sys_created_on DESC LIMIT 1",
            (batch_number,)
        ).fetchone()
        log = conn.execute(
            "SELECT * FROM ws_compliance_log WHERE batch_number=? ORDER BY sys_created_on DESC",
            (batch_number,)
        ).fetchall()
        return {
            "batch": dict(batch) if batch else None,
            "coa": dict(coa) if coa else None,
            "compliance_log": [dict(r) for r in log]
        }
    finally:
        conn.close()

@router.get("/api/wildseed/products")
async def ws_products():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT p.*, 
                   COALESCE(SUM(i.units_on_hand),0) as total_on_hand,
                   COALESCE(SUM(i.units_pending_lab),0) as total_pending,
                   COALESCE(SUM(i.units_shipped),0) as total_shipped
            FROM ws_product p
            LEFT JOIN ws_inventory i ON i.sku = p.sku
            WHERE p.active = 1
            GROUP BY p.sku
            ORDER BY p.category, p.name
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.get("/api/wildseed/coas")
async def ws_coas():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM ws_coa ORDER BY sys_created_on DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.get("/api/wildseed/compliance")
async def ws_compliance():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM ws_compliance_log ORDER BY sys_created_on DESC LIMIT 100"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── WEEDSTACK M.A.R.D ENGINE API ENDPOINTS ───────────────────────────────────

@router.get("/api/weedstack/sources")
async def ws_sources(user=Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM ws_content_source WHERE room_key='WEEDSTACK_SIM_001' ORDER BY enabled DESC, source_key"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.post("/api/weedstack/sources/{source_key}/toggle")
async def toggle_source(source_key: str, request: Request, user=Depends(get_current_user)):
    if user.get("role") not in ("pilot", "admin", "creator"):
        raise HTTPException(status_code=403, detail="Permission denied")
    body = await request.json()
    enabled = 1 if body.get("enabled") else 0
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE ws_content_source SET enabled=? WHERE source_key=?",
            (enabled, source_key)
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "ok", "source_key": source_key, "enabled": bool(enabled)}

@router.post("/api/weedstack/inject")
async def manual_inject(request: Request, user=Depends(get_current_user)):
    if user.get("role") not in ("pilot", "admin"):
        raise HTTPException(status_code=403, detail="Permission denied")
    body = await request.json()
    import uuid
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO ws_content_event
                (sys_id, source_key, room_key, headline, content, tags)
            VALUES (?, 'custom', 'WEEDSTACK_SIM_001', ?, ?, ?)
        """, (uuid.uuid4().hex, body["headline"], body["content"], body.get("tags", "")))
        conn.commit()
    finally:
        conn.close()
    return {"status": "queued", "headline": body["headline"]}

@router.get("/api/weedstack/factions")
async def ws_factions(user=Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        factions = conn.execute(
            "SELECT * FROM ws_faction WHERE room_key='WEEDSTACK_SIM_001'"
        ).fetchall()
        members = conn.execute("""
            SELECT m.faction_id, m.persona_name, m.role, p.display_name, p.color
            FROM ws_faction_member m
            JOIN persona p ON p.user_name = m.persona_name
        """).fetchall()
        return {
            "factions": [dict(f) for f in factions],
            "members": [dict(m) for m in members]
        }
    finally:
        conn.close()
