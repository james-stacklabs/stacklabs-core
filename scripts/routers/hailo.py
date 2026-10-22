from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil
from datetime import datetime, timedelta, timezone
from core.db import DB_PATH, get_db
from core.security import get_current_user, require_pilot, require_manager_or_pilot, security

router = APIRouter()

# FLAG FOR JAMES: LOG_FILE was referenced in get_hailo_logs() but never defined
# anywhere in the original monolith -- this was a pre-existing NameError waiting to
# happen on every call to GET /api/hailo/logs. Guessed a path below; confirm/correct it.
LOG_FILE = "/home/james/stacklabs/logs/hailo_classifier.log"


class HailoApproveRequest(BaseModel):
    sys_id: str
    advocate: str

class HailoDiscardRequest(BaseModel):
    sys_id: str

@router.get("/api/hailo/backlog")
def get_hailo_backlog():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT sys_id, advocate, expression, file_path, sha256, sys_created_on 
            FROM cmdb_ci_media_asset 
            WHERE expression LIKE 'unassigned_hailo_candidate%'
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/api/hailo/approve")
def approve_hailo_asset(req: HailoApproveRequest):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM cmdb_ci_media_asset WHERE sys_id = ?", (req.sys_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found")
            
        src_relative_path = row["file_path"] # e.g. /backlog/tile_0_0.png
        src_abs_path = f"/home/james/stacklabs/01_Sovereign_Portal/public{src_relative_path}"
        
        dest_dir = f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{req.advocate}"
        os.makedirs(dest_dir, exist_ok=True)
        dest_relative_path = f"/avatars/{req.advocate}/front_neutral.png"
        dest_abs_path = f"/home/james/stacklabs/01_Sovereign_Portal/public{dest_relative_path}"
        
        if os.path.exists(src_abs_path):
            shutil.copy2(src_abs_path, dest_abs_path)
            # Remove the source backlog file
            try:
                os.remove(src_abs_path)
            except Exception:
                pass
        else:
            raise HTTPException(status_code=404, detail="Source image file not found on disk")
            
        # Update cmdb_ci_media_asset
        cur.execute("""
            UPDATE cmdb_ci_media_asset
            SET expression = 'front_neutral', advocate = ?, file_path = ?
            WHERE sys_id = ?
        """, (req.advocate, dest_relative_path, req.sys_id))
        
        # Update persona avatar_url
        cur.execute("""
            UPDATE persona
            SET avatar_url = ?
            WHERE user_name = ?
        """, (dest_relative_path, req.advocate))
        
        conn.commit()
        return {"status": "success", "dest": dest_relative_path}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/api/hailo/discard")
def discard_hailo_asset(req: HailoDiscardRequest):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM cmdb_ci_media_asset WHERE sys_id = ?", (req.sys_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found")
            
        src_relative_path = row["file_path"]
        src_abs_path = f"/home/james/stacklabs/01_Sovereign_Portal/public{src_relative_path}"
        
        if os.path.exists(src_abs_path):
            try:
                os.remove(src_abs_path)
            except Exception:
                pass
                
        cur.execute("DELETE FROM cmdb_ci_media_asset WHERE sys_id = ?", (req.sys_id,))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/api/hailo/logs")
def get_hailo_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()
            return {"logs": [line.strip() for line in lines[-30:]]}
        except Exception as e:
            return {"logs": [f"Error reading log file: {e}"]}
    return {"logs": ["Log file not found."]}

@router.post("/api/hailo/run_classifier")
def run_hailo_classifier():
    try:
        cmd = "/home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/hailo_asset_classifier.py"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            raise HTTPException(status_code=500, detail=res.stderr or res.stdout)
        return {"status": "success", "output": res.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
