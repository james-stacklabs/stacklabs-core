from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil
from datetime import datetime, timedelta, timezone
from core.db import DB_PATH, get_db
from core.security import get_current_user, require_pilot, require_manager_or_pilot, security

router = APIRouter()


# ── End Theater Remote Relay ───────────────────────────────────────────────

# ── Sovereign Ingestor API (STRY1779446316) ────────────────────────────────
# POST /api/ingest — bulk insert tickets into sovereign_tickets
# Accepts: JSON array of ticket objects
# Returns: per-row success/error report

DB_INGEST_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
VALID_TYPES = {"STRY", "DFCT", "ENHC", "INC", "REQ"}

CORS_HEADERS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "*"}


def _parse_int_field(val, default: int, label: str, mapping: dict = None) -> int:
    """Safely coerce priority/state fields — handles int, string int, or mapped labels (P1/HIGH etc)."""
    if val is None:
        return default
    if mapping and str(val).upper() in mapping:
        return mapping[str(val).upper()]
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

PRIORITY_MAP = {"P1": 1, "P2": 2, "P3": 3, "CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 3, "STANDARD": 3}
STATE_MAP    = {"OPEN": 1, "IN_PROGRESS": 2, "TESTING": 3, "RESOLVED": 4, "DONE": 4, "CLOSED": 5, "PLANNING": 0}

@router.post("/api/ingest")
async def sovereign_ingest(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, list):
        body = [body]  # accept single object too

    results = []
    conn = sqlite3.connect(DB_INGEST_PATH)
    c = conn.cursor()

    for item in body:
        number   = item.get("number", "").strip()
        typ      = item.get("type", "STRY").strip().upper()
        short    = item.get("short_description", "").strip()
        desc     = item.get("description", "").replace("\n", " ").replace("\r", "")
        state    = _parse_int_field(item.get("state", 1),    1, "state",    STATE_MAP)
        priority = _parse_int_field(item.get("priority", 3), 3, "priority", PRIORITY_MAP)
        assigned = item.get("assigned_to", "")
        ci       = item.get("cmdb_ci", "")
        notes    = item.get("work_notes", "")
        parent   = item.get("parent_sys_id", None)
        sys_id   = item.get("sys_id") or uuid.uuid4().hex

        if typ not in VALID_TYPES:
            results.append({"number": number, "status": "error", "detail": f"Invalid type '{typ}'. Must be one of {VALID_TYPES}"})
            continue
        if not number:
            results.append({"number": "(missing)", "status": "error", "detail": "number field is required"})
            continue

        try:
            c.execute("""
                INSERT INTO sovereign_tickets
                  (sys_id, number, type, parent_sys_id, short_description, description,
                   state, priority, assigned_to, cmdb_ci, work_notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (sys_id, number, typ, parent, short, desc, state, priority, assigned, ci, notes))
            conn.commit()
            results.append({"number": number, "status": "ok", "sys_id": sys_id})
        except sqlite3.IntegrityError as e:
            conn.rollback()
            results.append({"number": number, "status": "error", "detail": f"UNIQUE constraint: {e}"})
        except Exception as e:
            conn.rollback()
            results.append({"number": number, "status": "error", "detail": str(e)})

    conn.close()
    ok_count  = sum(1 for r in results if r["status"] == "ok")
    err_count = len(results) - ok_count
    return {"ingested": ok_count, "errors": err_count, "results": results}


@router.post("/api/ingress")
@router.get("/api/ingress")
async def api_ingress():
    try:
        # Play physical chime
        print("\n🔔 [VIP INGRESS DETECTED] Wardy has entered the Sandbox 🔔\n")
        try:
            subprocess.Popen(['paplay', '/usr/share/sounds/freedesktop/stereo/message.oga'], stderr=subprocess.DEVNULL)
        except Exception:
            print('\a') # Fallback to terminal bell
            
        # Log to DB Severity 0
        conn = sqlite3.connect(DB_INGEST_PATH)
        c = conn.cursor()
        try:
            c.execute('CREATE TABLE IF NOT EXISTS sys_alerts (timestamp TEXT, severity INTEGER, message TEXT, sys_created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP, sys_updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
            c.execute('INSERT INTO sys_alerts (timestamp, severity, message) VALUES (?, ?, ?)', 
                      (datetime.now().isoformat(), 0, '[VIP INGRESS DETECTED] Wardy connected to FanStack Sandbox'))
            conn.commit()
        finally:
            conn.close()
            
        return JSONResponse(content={"status": "ingress_logged"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

