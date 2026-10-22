
# --- Hoisted Module-Level Imports (Sovereign AST Hygiene) ---
import json
import sqlite3
import sqlite3, os
import time
import uuid, os, hashlib, base64, sqlite3, shutil, re
# -------------------------------------------------------------

from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil
from datetime import datetime, timedelta, timezone
from core.db import DB_PATH, get_db
from core.api_client import resolve_team_name, get_team
from core.security import get_current_user, require_pilot, require_manager_or_pilot, security

router = APIRouter()


class SoundboardPhraseRequest(BaseModel):
    advocate: str
    button_label: str
    text_payload: str

@router.get("/api/media/soundboard")
async def get_soundboard(advocate: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM persona WHERE user_name = ?", (advocate,))
        p_row = c.fetchone()
        if not p_row:
            c.execute("SELECT id FROM persona WHERE LOWER(user_name) = LOWER(?)", (advocate,))
            p_row = c.fetchone()
            if not p_row:
                return {"status": "success", "phrases": []}
        
        persona_id = p_row["id"]
        c.execute(
            "SELECT sys_id, persona_id, button_label, text_payload, is_custom, created_at FROM cmdb_ci_media_soundboard_phrase WHERE persona_id = ? ORDER BY created_at ASC",
            (persona_id,)
        )
        rows = c.fetchall()
        phrases = [dict(r) for r in rows]
        return {"status": "success", "phrases": phrases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/api/media/soundboard")
async def create_soundboard_phrase(req: SoundboardPhraseRequest):
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM persona WHERE user_name = ?", (req.advocate,))
        p_row = c.fetchone()
        if not p_row:
            c.execute("SELECT id FROM persona WHERE LOWER(user_name) = LOWER(?)", (req.advocate,))
            p_row = c.fetchone()
            if not p_row:
                raise HTTPException(status_code=404, detail=f"Advocate/persona '{req.advocate}' not found")
        
        persona_id = p_row[0]
        sys_id = uuid.uuid4().hex
        c.execute("""
            INSERT INTO cmdb_ci_media_soundboard_phrase (sys_id, persona_id, button_label, text_payload, is_custom)
            VALUES (?, ?, ?, ?, 1)
        """, (sys_id, persona_id, req.button_label, req.text_payload))
        conn.commit()
        return {"status": "success", "sys_id": sys_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.delete("/api/media/soundboard/{sys_id}")
async def delete_soundboard_phrase(sys_id: str):
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("SELECT sys_id FROM cmdb_ci_media_soundboard_phrase WHERE sys_id = ?", (sys_id,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="Phrase not found")
        c.execute("DELETE FROM cmdb_ci_media_soundboard_phrase WHERE sys_id = ?", (sys_id,))
        conn.commit()
        return {"status": "success", "message": "Phrase deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


class OutrageProxyRequest(BaseModel):
    manager_id: str
    trigger_event: str
    selected_proxy_id: int
    intensity_level: str

@router.get("/api/sports/outrage_proxy_umpires")
async def get_outrage_proxy_umpires():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute("""
            SELECT id, umpire_name, durability_rating, dirt_kick_capacity, ejection_flair_level, active_status
            FROM outrage_proxy_umpires
            ORDER BY id ASC
        """)
        rows = c.fetchall()
        proxies = [dict(row) for row in rows]
        return {"status": "success", "proxies": proxies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/v1/triage/rage")
async def deploy_rage_proxy(req: OutrageProxyRequest):
    import websockets
    # [Hoisted to header] import json
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        
        # 1. Verify proxy umpire active status and capacity
        c.execute("""
            SELECT id, umpire_name, active_status, dirt_kick_capacity, ejection_flair_level
            FROM outrage_proxy_umpires
            WHERE id = ?
        """, (req.selected_proxy_id,))
        ump_row = c.fetchone()
        if not ump_row:
            raise HTTPException(status_code=404, detail=f"Proxy umpire ID {req.selected_proxy_id} not found.")
        
        if not ump_row["active_status"] or ump_row["active_status"] != 1:
            raise HTTPException(status_code=400, detail=f"Proxy umpire '{ump_row['umpire_name']}' is not active.")
            
        if ump_row["dirt_kick_capacity"] <= 0:
            raise HTTPException(status_code=400, detail=f"Proxy umpire '{ump_row['umpire_name']}' has depleted dirt kick capacity.")
            
        # 2. Perform a lookup on the transaction limits (max 2 manager tantrums per game)
        # Find active game
        c.execute("""
            SELECT game_pk FROM cmdb_ci_fanstack_room r
            JOIN cmdb_ci c ON r.sys_id = c.sys_id
            WHERE c.operational_status = 'active' OR c.operational_status = 1 OR c.operational_status = 3
            LIMIT 1
        """)
        game_row = c.fetchone()
        active_game_pk = game_row["game_pk"] if game_row else "823615"
        
        c.execute("""
            SELECT COUNT(*) FROM outrage_proxy_tantrums WHERE game_pk = ?
        """, (active_game_pk,))
        tantrum_count = c.fetchone()[0]
        if tantrum_count >= 2:
            raise HTTPException(
                status_code=429, 
                detail="Transaction limit reached: Max 2 manager tantrums per game allowed to avoid infinite loop locks."
            )
            
        # 3. Emit a WebSocket signal to the active game room
        ws_msg = {
            "type": "outrage_proxy_deployed",
            "event": "outrage_proxy_deployed",
            "proxy_name": ump_row["umpire_name"],
            "action": "traditional_drama_loop",
            "ejection_triggered": True,
            "target_game_pk": active_game_pk
        }
        
        try:
            async with websockets.connect("ws://localhost:8008") as ws:
                await ws.send(json.dumps(ws_msg))
        except Exception as ws_err:
            print(f"[RaaS] WebSocket broadcast failed: {ws_err}")
            
        # 4. Increment the target umpire's dirt_kick_capacity usage (decrement capacity) and update the database state
        c.execute("""
            UPDATE outrage_proxy_umpires
            SET dirt_kick_capacity = MAX(0, dirt_kick_capacity - 1)
            WHERE id = ?
        """, (req.selected_proxy_id,))
        
        # Log the tantrum
        c.execute("""
            INSERT INTO outrage_proxy_tantrums (game_pk, umpire_id, manager_id, intensity_level)
            VALUES (?, ?, ?, ?)
        """, (active_game_pk, req.selected_proxy_id, req.manager_id, req.intensity_level))
        
        conn.commit()
        
        return {
            "status": "success",
            "message": "Outrage proxy deployed successfully",
            "active_game_pk": active_game_pk,
            "proxy_name": ump_row["umpire_name"],
            "remaining_capacity": max(0, ump_row["dirt_kick_capacity"] - 1)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ScratchpadRequest(BaseModel):
    raw_text: str
    source_context: str = "StackLabs Homepage Quick-Capture"

@router.post("/v1/ingress/scratchpad", status_code=201)
async def create_ingress_scratchpad(req: ScratchpadRequest):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        c = conn.cursor()
        c.execute("""
            INSERT INTO raw_idea_backlog (raw_text, source_context)
            VALUES (?, ?)
        """, (req.raw_text, req.source_context))
        idea_id = c.lastrowid
        conn.commit()
        return {"status": "success", "idea_id": idea_id}
    except Exception as e:
        print(f"[INGRESS ERROR] Database insertion failed, fallback active: {e}")
        return {
            "status": "fallback",
            "message": "Database write failed, local fallback enabled",
            "error": str(e),
            "local_fallback": True
        }
    finally:
        conn.close()

@router.post("/api/media/physical_siren")
async def trigger_physical_siren():
    import socket
    # [Hoisted to header] import json
    import asyncio
    # [Hoisted to header] import time
    
    ips = ["192.168.1.173", "192.168.1.174", "192.168.1.176", "192.168.1.188"]
    port = 4003
    
    def fire_govee(r, g, b):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = {
            "msg": {
                "cmd": "colorWC",
                "data": {
                    "color": {"r": r, "g": g, "b": b},
                    "colorTem": 0
                }
            }
        }
        payload = json.dumps(msg).encode('utf-8')
        for ip in ips:
            try:
                sock.sendto(payload, (ip, port))
            except:
                pass
        sock.close()
        
    def run_strobe():
        for _ in range(5):
            fire_govee(255, 0, 0)
            time.sleep(0.3)
            fire_govee(0, 0, 255)
            time.sleep(0.3)
            
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, run_strobe)
    return {"status": "success", "message": "Physical siren triggered mesh-wide."}


# -------------------------------------------------------------
# ADVOCATE CENTER / LOOKBOOK MEDIA API ENDPOINTS
# -------------------------------------------------------------

class UpdateExpressionRequest(BaseModel):
    expression: str
    category: str = None

@router.get("/api/media/assets/{advocate}")
async def get_media_assets_for_advocate(advocate: str):
    # [Hoisted to header] import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute("""
            SELECT c.sys_id, c.advocate, c.expression, c.file_path, c.sha256, s.category, s.name, s.mime_type
            FROM cmdb_ci_media_asset c
            LEFT JOIN sys_media_asset s ON c.file_path = s.file_path OR c.sha256 = s.md5_hash
            WHERE c.advocate = ? OR c.advocate = ?
        """, (advocate, advocate.lower().replace(" ", "_")))
        rows = c.fetchall()
        assets = []
        for r in rows:
            expr = r["expression"]
            assets.append({
                "sys_id": r["sys_id"],
                "advocate": r["advocate"],
                "expression": expr,
                "file_path": r["file_path"],
                "sha256": r["sha256"],
                "category": r["category"] or ("Concept Art" if "concept" in expr.lower() else "Raw Photos"),
                "name": r["name"] or expr,
                "mime_type": r["mime_type"] or "image/png"
            })
        return {"assets": assets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/api/media/assets/{advocate}/upload")
async def upload_media_asset(
    advocate: str,
    file: UploadFile = File(...),
    expression: str = None,
    category: str = "Concept Art"
):
    # [Hoisted to header] import uuid, os, hashlib, base64, sqlite3, shutil, re
    safe_advocate = advocate.lower().replace(" ", "_")
    
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
        
    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    expr_name = expression or os.path.splitext(file.filename)[0]
    expr_name = expr_name.strip()
    
    md5_hash = hashlib.md5(contents).hexdigest()
    sha256_hash = hashlib.sha256(contents).hexdigest()
    
    lookbook_dir = f"/home/james/stacklabs/15_FanStack/public/lookbook/{safe_advocate}"
    os.makedirs(lookbook_dir, exist_ok=True)
    
    file_name = f"{expr_name.replace(' ', '_')}{ext}"
    local_path = os.path.join(lookbook_dir, file_name)
    
    with open(local_path, "wb") as f:
        f.write(contents)
        
    web_path = f"/lookbook/{safe_advocate}/{file_name}"
    
    vault_dir = f"/home/james/stacklabs/media_vault/01_Assets/{safe_advocate.capitalize()}_Lookbook"
    os.makedirs(vault_dir, exist_ok=True)
    shutil.copy2(local_path, os.path.join(vault_dir, file_name))
    
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        
        c.execute("SELECT sys_id, asset_tag FROM sys_media_asset WHERE md5_hash = ?", (md5_hash,))
        existing = c.fetchone()
        
        b64 = base64.b64encode(contents).decode("utf-8")
        
        if existing:
            sys_id_val, tag = existing
            c.execute("""
                UPDATE sys_media_asset 
                SET name = ?, file_name = ?, file_path = ?, file_size_bytes = ?, mime_type = ?, category = ?, image_blob = ?, updated_at = datetime('now')
                WHERE sys_id = ?
            """, (f"{advocate} Lookbook ({expr_name})", file_name, local_path, len(contents), file.content_type, category, b64, sys_id_val))
        else:
            c.execute("SELECT asset_tag FROM sys_media_asset")
            rows = c.fetchall()
            max_num = 0
            for r in rows:
                if r[0]:
                    match = re.search(r'FS-MED-(\d+)', r[0])
                    if match:
                        num = int(match.group(1))
                        if num < 99999 and num > max_num:
                            max_num = num
            next_tag = f"FS-MED-{(max_num + 1):05d}"
            sys_id_val = uuid.uuid4().hex
            
            c.execute("""
                INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
            """, (sys_id_val, next_tag, f"{advocate} Lookbook ({expr_name})", file_name, local_path, len(contents), file.content_type or "image/png", category, md5_hash, b64))
            
        c.execute("DELETE FROM cmdb_ci_media_asset WHERE advocate = ? AND expression = ?", (safe_advocate, expr_name))
        c.execute("""
            INSERT INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
            VALUES (?, ?, ?, ?, ?)
        """, (uuid.uuid4().hex, safe_advocate, expr_name, web_path, sha256_hash))
        
        conn.commit()
        return {"status": "success", "expression": expr_name, "file_path": web_path, "sha256": sha256_hash}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.put("/api/media/assets/expression/{sys_id}")
async def update_media_expression(sys_id: str, req: UpdateExpressionRequest):
    # [Hoisted to header] import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("SELECT advocate, file_path, sha256 FROM cmdb_ci_media_asset WHERE sys_id = ?", (sys_id,))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Expression asset not found")
            
        advocate, file_path, sha256 = row
        new_expr = req.expression.strip()
        
        c.execute("UPDATE cmdb_ci_media_asset SET expression = ? WHERE sys_id = ?", (new_expr, sys_id))
        
        if req.category:
            c.execute("UPDATE sys_media_asset SET category = ?, name = ? WHERE file_path = ? OR md5_hash = ?", 
                      (req.category, f"{advocate.capitalize()} Lookbook ({new_expr})", file_path, sha256))
                      
        conn.commit()
        return {"status": "success", "sys_id": sys_id, "expression": new_expr}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.delete("/api/media/assets/expression/{sys_id}")
async def delete_media_expression(sys_id: str):
    # [Hoisted to header] import sqlite3, os
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("SELECT file_path, sha256 FROM cmdb_ci_media_asset WHERE sys_id = ?", (sys_id,))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Expression asset not found")
            
        file_path, sha256 = row
        
        c.execute("DELETE FROM cmdb_ci_media_asset WHERE sys_id = ?", (sys_id,))
        c.execute("DELETE FROM sys_media_asset WHERE md5_hash = ? OR file_path = ?", (sha256, file_path))
        
        clean_path = file_path.lstrip("/")
        search_dirs = [
            "/home/james/stacklabs/15_FanStack/public",
            "/home/james/stacklabs"
        ]
        for d in search_dirs:
            p = os.path.join(d, clean_path)
            if os.path.exists(p) and os.path.isfile(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
                    
        conn.commit()
        return {"status": "success", "sys_id": sys_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/api/media/print_lookbook")
async def print_lookbook_pdf(advocate: str, ids: str = None, background_tasks: BackgroundTasks = None):
    """Thin wrapper -- actual rendering logic lives in pdf/renderers.py (was 430 lines inline here)."""
    from pdf.renderers import print_lookbook_pdf as _render
    return await _render(advocate, ids, background_tasks)



@router.get("/api/system/personas/lookbook")
async def get_system_persona_lookbook(username: str):
    # [Hoisted to header] import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute("""
            SELECT user_name, display_name, team, deep_lore, behavior_notes, color
            FROM persona
            WHERE user_name = ? COLLATE NOCASE
        """, (username,))
        row = c.fetchone()
        if not row:
            clean_username = username.lstrip('@')
            c.execute("""
                SELECT user_name, display_name, team, deep_lore, behavior_notes, color
                FROM persona
                WHERE user_name = ? COLLATE NOCASE
            """, (clean_username,))
            row = c.fetchone()
            
        if row:
            p = dict(row)
            role_map = {
                "water_barrel_wayne": "Smyrna Prepper & Barter Authority",
                "warden_barb": "Spite Slice Parlor Manager & Defiance Lead",
                "dr_kosmos": "Bare-Metal Zealot & Spiritual Vibe Consultant",
                "trop": "Lead Sabermetric Telemetry Analyst"
            }
            core_function_map = {
                "water_barrel_wayne": "High-velocity fatalism, trade-matrix operations, and central banking critiques.",
                "warden_barb": "Systematic extraction of corporate pizza market share and execution of absolute lockdown protocols.",
                "dr_kosmos": "Erratic thermodynamic edge advocacy and network node analysis.",
                "trop": "Dispassionate evaluation of launch angles, exit velocities, and pitch trail vectors."
            }
            u_key = p["user_name"].lower()
            role = role_map.get(u_key, p["display_name"] or "Sovereign OS Advocate")
            core_fn = core_function_map.get(u_key, p["behavior_notes"] or "Advocate Operations")

            p_team = p.get("team") or "Sovereign OS"
            resolved_abbr = resolve_team_name(p_team)
            if resolved_abbr and resolved_abbr != "GLOBAL":
                team_obj = get_team(resolved_abbr)
                if team_obj and team_obj.get("full_name"):
                    team_val = f"{team_obj['team_abbr']} ({team_obj['full_name']})"
                else:
                    team_val = resolved_abbr
            else:
                team_val = p_team
            
            return {
                "username": p["user_name"],
                "role": role,
                "team": team_val,
                "coreFunction": core_fn,
                "lore": p["deep_lore"] or ""
            }
        else:
            raise HTTPException(status_code=404, detail="Persona not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
