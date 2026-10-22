from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil
from datetime import datetime, timedelta, timezone
from core.db import DB_PATH, get_db
from core.api_client import get_team_color
from fastapi.security import HTTPAuthorizationCredentials
from core.security import (
    get_current_user, require_pilot, require_manager_or_pilot, security, _decode_token,
)

router = APIRouter()

def _get_vertex_project_id(default: str = "project-114213dc-6519-49c5-a0a") -> str:
    creds_path = "/home/james/stacklabs/config/vertex_sa.json"
    if os.path.exists(creds_path):
        try:
            with open(creds_path, "r") as f:
                data = json.load(f)
                return data.get("project_id", default)
        except Exception:
            pass
    return default


@router.get("/api/personas")
async def list_personas(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = None
    if credentials:
        try:
            user = _decode_token(credentials.credentials)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Pilot/admin or anonymous sees everything
        if not user or user.get("role") in ("pilot", "admin"):
            rows = conn.execute(
                "SELECT * FROM persona ORDER BY team, user_name"
            ).fetchall()
        else:
            role_team_map = {
                "garden_client": "WEEDSTACK",
                "creator": "WEEDSTACK",
            }
            team = role_team_map.get(user.get("role"))
            if not team:
                raise HTTPException(status_code=403, detail="No persona access for this role")
            rows = conn.execute(
                "SELECT * FROM persona WHERE team = ? ORDER BY user_name",
                (team,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.get("/api/personas/teams")
async def list_persona_teams(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = None
    if credentials:
        try:
            user = _decode_token(credentials.credentials)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if not user or user.get("role") in ("pilot", "admin"):
            rows = conn.execute(
                "SELECT DISTINCT team FROM persona ORDER BY team"
            ).fetchall()
            teams = [r["team"] for r in rows if r["team"]]
        else:
            role_team_map = {
                "garden_client": "WEEDSTACK",
                "creator": "WEEDSTACK",
            }
            team = role_team_map.get(user.get("role"))
            teams = [team] if team else []
        return {"teams": teams}
    finally:
        conn.close()

@router.get("/api/personas/print_dossier")
async def print_dossier_pdf(ids: str = None, background_tasks: BackgroundTasks = None):
    """Thin wrapper -- actual rendering logic lives in pdf/renderers.py (was 753 lines inline here)."""
    from pdf.renderers import print_dossier_pdf as _render
    return await _render(ids, background_tasks)



class PersonaTruthUpsertRequest(BaseModel):
    handle: str
    display_name: str
    role: str
    truth: str
    domain: str = "DAVINCIS_SMYRNA"
    is_heel: bool = False

@router.post("/api/personas/truth")
@router.post("/api/persona_truths/upsert")
async def upsert_persona_truth(req: PersonaTruthUpsertRequest):
    """Upsert a canonical persona truth into persona_truths table."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        user_name = req.handle.lstrip("@").lower()
        sys_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"truth:{req.domain}:{req.handle}").hex
        cur.execute("""
            INSERT INTO persona_truths (
                sys_id, handle, user_name, display_name, role, truth, domain, is_heel,
                sys_created_on, sys_updated_on, sys_created_by, sys_updated_by, sys_mod_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'clio', 'clio', 0)
            ON CONFLICT(handle) DO UPDATE SET
                display_name = excluded.display_name,
                role = excluded.role,
                truth = excluded.truth,
                domain = excluded.domain,
                is_heel = excluded.is_heel,
                sys_updated_on = CURRENT_TIMESTAMP,
                sys_mod_count = persona_truths.sys_mod_count + 1
        """, (sys_id, req.handle, user_name, req.display_name, req.role, req.truth, req.domain, 1 if req.is_heel else 0))
        conn.commit()
        return {"status": "SUCCESS", "handle": req.handle, "domain": req.domain, "sys_id": sys_id}
    finally:
        conn.close()

@router.get("/api/personas/truths")
@router.get("/api/persona_truths")
async def get_persona_truths(domain: Optional[str] = None):
    """Retrieve canonical persona truths from persona_truths table."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        if domain:
            cur.execute("SELECT * FROM persona_truths WHERE domain = ? ORDER BY handle", (domain,))
        else:
            cur.execute("SELECT * FROM persona_truths ORDER BY domain, handle")
        rows = [dict(r) for r in cur.fetchall()]
        return {"count": len(rows), "truths": rows}
    finally:
        conn.close()

@router.get("/api/personas/{persona_id}")
@router.get("/api/persona/{persona_id}")
async def get_persona(persona_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = None
    if credentials:
        try:
            user = _decode_token(credentials.credentials)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM persona WHERE id = ? OR user_name = ?", (persona_id, persona_id)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        # Enforce scoping if authenticated
        if user and user.get("role") not in ("pilot", "admin"):
            role_team_map = {"garden_client": "WEEDSTACK", "creator": "WEEDSTACK"}
            allowed_team = role_team_map.get(user.get("role"))
            if row["team"] != allowed_team:
                raise HTTPException(status_code=403, detail="You do not have access to this persona")
                
        return dict(row)
    finally:
        conn.close()

@router.get("/api/persona_image/{persona_id}")
async def get_persona_image(persona_id: str):
    import base64, sqlite3 as _sq, glob, os
    from fastapi.responses import Response, FileResponse, RedirectResponse
    
    # 0. Check if persona_id itself consists of digits. If so, redirect directly to MLB static.
    if persona_id.isdigit():
        return RedirectResponse(
            f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/{persona_id}/headshot/67/current"
        )
        
    safe_id = persona_id.lower().replace(" ", "_")
    requested_norm = persona_id.lower().replace(" ", "").replace("_", "").replace("-", "")
    
    # 1. Try DB first (canonical source of truth)
    matched_row = None
    try:
        con = _sq.connect(DB_PATH)
        rows = con.execute("SELECT avatar_blob, avatar_url, user_name, id FROM persona").fetchall()
        con.close()
        
        # 1a. Exact match
        for r in rows:
            db_user_norm = r[2].lower().replace(" ", "").replace("_", "").replace("-", "") if r[2] else ""
            db_id_norm = r[3].lower().replace(" ", "").replace("_", "").replace("-", "") if r[3] else ""
            if requested_norm == db_user_norm or requested_norm == db_id_norm:
                matched_row = r
                break
                
        # 1b. Fuzzy match
        if not matched_row:
            for r in rows:
                db_user_norm = r[2].lower().replace(" ", "").replace("_", "").replace("-", "") if r[2] else ""
                db_id_norm = r[3].lower().replace(" ", "").replace("_", "").replace("-", "") if r[3] else ""
                if (db_user_norm and (db_user_norm.startswith(requested_norm) or requested_norm.startswith(db_user_norm))) or \
                   (db_id_norm and (db_id_norm.startswith(requested_norm) or requested_norm.startswith(db_id_norm))):
                    matched_row = r
                    break
    except Exception as e:
        print(f"[persona_image] DB lookup error: {e}")
        
    if matched_row:
        # If DB blob exists, serve it
        if matched_row[0]:
            try:
                blob_data = matched_row[0]
                if blob_data.startswith('data:'):
                    header, b64 = blob_data.split(',', 1)
                    mime = header.split(':')[1].split(';')[0]
                else:
                    b64 = blob_data
                    mime = 'image/png'
                return Response(content=base64.b64decode(b64), media_type=mime)
            except Exception as e:
                print(f"[persona_image] error decoding base64 blob: {e}")
                
        # If DB url exists, try to serve file from disk
        if matched_row[1]:
            raw_url = matched_row[1].lstrip("/")
            for base_dir in [
                "/home/james/stacklabs",
                "/home/james/stacklabs/archive_quarantine_eon1",
                "/home/james/stacklabs/avatars",
                "/home/james/stacklabs/15_FanStack/public"
            ]:
                candidate = os.path.normpath(os.path.join(base_dir, raw_url))
                if os.path.exists(candidate) and os.path.isfile(candidate):
                    return FileResponse(candidate)
                    
    # 2. Fall back to filesystem search
    search_dirs = [
        "/home/james/stacklabs/avatars",
        "/home/james/stacklabs/archive_quarantine_eon1",
        "/home/james/stacklabs/15_FanStack/public/avatars",
        "/home/james/stacklabs/dna/media/avatars",
        "/home/james/stacklabs/dna/media/character_maps"
    ]
    
    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
            
        # 2a. Direct file check
        for f in glob.glob(os.path.join(search_dir, f"{safe_id}.*")):
            if f.lower().endswith(('.jpg','.jpeg','.png','.jfif','.webp','.svg')):
                return FileResponse(f)
                
        # 2b. Subdirectory check - prioritize files containing 'avatar'
        sub_dir = os.path.join(search_dir, safe_id)
        files_in_sub = []
        if os.path.isdir(sub_dir):
            files_in_sub = glob.glob(os.path.join(sub_dir, "*"))
            for f in files_in_sub:
                if 'avatar' in os.path.basename(f).lower() and f.lower().endswith(('.jpg','.jpeg','.png','.jfif','.webp','.svg')):
                    return FileResponse(f)
                    
        # 2c. Walk search - prioritize files containing 'avatar'
        found_walk_files = []
        for root, dirs, files in os.walk(search_dir):
            depth = root[len(search_dir):].count(os.sep)
            if depth > 1:
                continue
            for file in files:
                file_norm = os.path.splitext(file)[0].lower().replace(" ", "").replace("_", "").replace("-", "")
                if file_norm == requested_norm or file_norm.startswith(requested_norm) or requested_norm.startswith(file_norm):
                    f = os.path.join(root, file)
                    if f.lower().endswith(('.jpg','.jpeg','.png','.jfif','.webp','.svg')):
                        found_walk_files.append(f)
                        
        for f in found_walk_files:
            if 'avatar' in os.path.basename(f).lower():
                return FileResponse(f)
                
        # 2d. Subdirectory check fallback (any image)
        if os.path.isdir(sub_dir):
            for f in files_in_sub:
                if f.lower().endswith(('.jpg','.jpeg','.png','.jfif','.webp','.svg')):
                    return FileResponse(f)
                    
        # 2e. Walk search fallback (any image)
        if found_walk_files:
            return FileResponse(found_walk_files[0])

    # 3. Fall back to mlb_rosters table matching name
    try:
        search_name = safe_id.replace("_", " ")
        con = _sq.connect(DB_PATH)
        row = con.execute(
            "SELECT sys_id FROM mlb_rosters WHERE LOWER(player_name) = ?",
            (search_name,)
        ).fetchone()
        con.close()
        if row and row[0]:
            sys_id = row[0]
            numeric_id = "".join([c for c in sys_id if c.isdigit()])
            if numeric_id:
                return RedirectResponse(
                    f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/{numeric_id}/headshot/67/current"
                )
    except Exception as e:
        print(f"[persona_image] MLB roster lookup error: {e}")
        
    # 4. Final fallback: return the no_clue placeholder
    fallback_path = "/home/james/stacklabs/archive_quarantine_eon1/no_clue.jpg"
    if os.path.exists(fallback_path):
        return FileResponse(fallback_path)
        
    raise HTTPException(status_code=404, detail="Image not found")


@router.post("/api/persona_image/{persona_id}")
async def upload_persona_image_blob(persona_id: str, file: UploadFile = File(...)):
    """Store avatar as base64 blob in persona.avatar_blob — no filesystem, no rebuild needed."""
    import base64, sqlite3 as _sq
    safe_id = persona_id.lower().replace(" ", "_")
    raw = await file.read()
    mime = file.content_type or 'image/png'
    b64 = base64.b64encode(raw).decode('utf-8')
    data_url = f"data:{mime};base64,{b64}"
    avatar_path = f"/api/persona_image/{safe_id}"
    con = _sq.connect(DB_PATH)
    updated = con.execute(
        "UPDATE persona SET avatar_blob = ?, avatar_url = ? WHERE LOWER(user_name) = ? OR LOWER(id) = ?",
        (data_url, avatar_path, safe_id, safe_id)
    ).rowcount
    if updated > 0:
        con.execute(
            "UPDATE sys_user SET avatar_url = ? WHERE sys_id = (SELECT id FROM persona WHERE LOWER(user_name) = ? OR LOWER(id) = ?)",
            (avatar_path, safe_id, safe_id)
        )
    con.commit()
    con.close()
    if updated == 0:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")
    return {"status": "success", "user_name": safe_id, "avatar_url": avatar_path}


@router.get("/api/personas/{user_name}/posts")
async def get_persona_posts(user_name: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = None
    if credentials:
        try:
            user = _decode_token(credentials.credentials)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Check access: non-pilots can only view their own team's personas' posts
        if user and user.get("role") not in ("pilot", "admin"):
            role_team_map = {"garden_client": "WEEDSTACK", "creator": "WEEDSTACK"}
            allowed_team = role_team_map.get(user.get("role"))
            
            p = conn.execute("SELECT team FROM persona WHERE user_name = ?", (user_name,)).fetchone()
            if not p or p["team"] != allowed_team:
                raise HTTPException(status_code=403, detail="You do not have access to this persona's posts")
        
        rows = conn.execute(
            "SELECT text, created_at, game_pk FROM game_chat WHERE persona = ? ORDER BY id DESC LIMIT 5",
            (user_name,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.patch("/api/personas/{persona_id}")
async def update_persona(persona_id: str, request: Request, user=Depends(get_current_user)):
    data = await request.json()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Check if the persona exists
        existing = conn.execute(
            "SELECT id, team, boggs_level FROM persona WHERE id = ? OR user_name = ?", (persona_id, persona_id)
        ).fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Persona not found")

        # Non-pilots can only edit their own team's personas
        if user.get("role") not in ("pilot", "admin"):
            role_team_map = {"garden_client": "WEEDSTACK", "creator": "WEEDSTACK"}
            allowed_team = role_team_map.get(user.get("role"))
            if existing["team"] != allowed_team:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to edit this persona"
                )

        # Map frontend key style
        field_map = {
            "user_name":               "user_name",
            "first_name":              "display_name",
            "assigned_to":             "team",
            "u_system_prompt":         "system_prompt",
            "u_cadence":               "cadence",
            "u_boggs_reactivity":      "boggs_level",
            "u_behavior_expectations": "behavior_notes",
            "u_deep_lore":             "deep_lore",
            "u_governance_boundaries": "governance",
            "color":                   "color",
            "email_alias":             "email_alias",
            "avatar_url":              "avatar_url",
            "active":                  "active",
        }

        updates = {}
        for k, v in data.items():
            col = field_map.get(k) or k
            updates[col] = v

        # Restrict which fields non-pilots can update
        NON_PILOT_EDITABLE = {"display_name", "avatar_url", "boggs_level"}

        if user.get("role") not in ("pilot", "admin"):
            updates = {k: v for k, v in updates.items() if k in NON_PILOT_EDITABLE}

            # Cap boggs_level at 3 for non-pilots
            if "boggs_level" in updates and updates["boggs_level"] is not None:
                updates["boggs_level"] = min(int(updates["boggs_level"]), 3)

        if not updates:
            return {"status": "no_changes"}

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [existing["id"]]
        conn.execute(f"UPDATE persona SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return {"status": "updated", "persona_id": existing["id"]}
    finally:
        conn.close()


@router.get("/api/style_registry")
async def get_style_registry():
    import json
    config_path = "/home/james/stacklabs/config/style_registry.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[style_registry] Error reading config: {e}")
    
    # Fallback registry if file is missing or corrupted
    return {
        "styles": [
            {
                "id": "90s_cardboard_comic",
                "display_name": "90s Cardboard Comic",
                "prompt_tokens": "Hand-drawn ink line-art contours, Calvin and Hobbes style, soft watercolor washes, hand-drawn dialogue bubbles, cardboard and duct tape textures, cozy 90s treehouse aesthetic",
                "reference_asset": "image_35b3f6.jpg",
                "best_use_case": "Core FanStack advocate series & Smyrna Heights neighborhood sandbox"
            }
        ]
    }


# ==============================================================================
# UNIVERSAL WILDCARD ADVOCATE FORGE ENDPOINTS (WO-2026-0829)
# ==============================================================================

class ForgeMagicAssistRequest(BaseModel):
    field: str
    name: Optional[str] = ""
    team: Optional[str] = "GLOBAL"
    cadence: Optional[str] = "pacer"
    current_text: Optional[str] = ""

class ForgeSynthesizeRequest(BaseModel):
    name: str
    concept: str
    team: str = "GLOBAL"
    cadence: str = "pacer"
    boggs_level: int = 2
    color: str = "#00b4d8"

class ForgeDeployRequest(BaseModel):
    handle: str
    display_name: str
    team: str = "GLOBAL"
    system_prompt: str
    deep_lore: str
    behavior_notes: str = ""
    governance: str = ""
    color: str = "#00b4d8"
    cadence: str = "pacer"
    boggs_level: int = 2
    avatar_url: str = ""
    rooms: list[str] = []
    canned_takes: list[str] = []
    page1_executive: str = ""
    page2_conflicts: str = ""
    page3_sanctuary: str = ""
    page4_deflections: str = ""
    page5_metadata: str = ""
    reference_artwork: Optional[dict] = None

@router.get("/api/system/forge/rooms")
async def get_forge_rooms():
    """Returns dynamic active room candidates for persona seating."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT room FROM m2m_persona_room WHERE room IS NOT NULL AND room != ''")
        db_rooms = [r["room"] for r in cur.fetchall()]
        
        core_presets = [
            "global",
            "scruffys",
            "gonzas_cantina",
            "spite_slice",
            "WILDSEED_SIM_001",
            "STACKLABS_SIM_001",
            "rm_nfl_blunderdome",
            "ttrpg_campaign_room_01"
        ]
        
        # Merge and deduplicate
        all_rooms = sorted(list(set(core_presets + db_rooms)))
        return {"rooms": all_rooms}
    finally:
        conn.close()

@router.post("/api/system/forge/synthesize")
async def synthesize_advocate(req: ForgeSynthesizeRequest):
    """
    Synthesizes a full 4-phase advocate dossier and cognitive matrix using Vertex AI Gemini
    with structured schema guarantees and high-fidelity fallback.
    """
    clean_handle = re.sub(r'[^a-z0-9_]', '', req.name.lower().replace(' ', '_')).strip('_') or "wildcard_advocate"
    
    project_id = _get_vertex_project_id()
    location = "us-central1"
    credentials_path = "/home/james/stacklabs/config/vertex_sa.json"
    
    sys_instruction = f"""
    You are the Sovereign OS Deep Lore & Cognitive Architecture Engine.
    Synthesize an authentic, high-fidelity AI advocate persona for Sovereign OS.
    
    Advocate Name: {req.name}
    Concept/Vibe: {req.concept}
    Team/Faction: {req.team}
    Cadence: {req.cadence}
    Boggs Reactivity Level: {req.boggs_level} (1-5 scale)
    
    You MUST return a JSON object matching this schema EXACTLY:
    {{
      "display_name": "{req.name}",
      "handle": "{clean_handle}",
      "role": "Archetype / Job Title",
      "team": "{req.team}",
      "cadence": "{req.cadence}",
      "boggs_level": {req.boggs_level},
      "color": "{req.color}",
      "dossier": {{
        "page1_executive": "Page 1: Executive Profile, Public Identity, Secret Identity & Psychological Invariants (~200 words)",
        "page2_conflicts": "Page 2: High-Stakes Real-World Conflicts, Adversaries & Paranoia Triggers (~200 words)",
        "page3_sanctuary": "Page 3: Secret Hobby Sanctuary, Crafting Obsessions & Private Space (~200 words)",
        "page4_deflections": "Page 4: Dual-Social Deflections, Alibis & Defense Excuses (~200 words)",
        "page5_metadata": "Page 5: Ingress Metadata: Handle: @{clean_handle} | Team: {req.team} | Protocol: M.A.R.D. v2.4 | Priority: Alpha"
      }},
      "cognitive_matrix": {{
        "system_prompt": "Master Instructions (~500 words). Detailed rules of engagement, tone, banter hooks, and response constraints.",
        "governance_rules": [
          "Rule 1: Strict adherence to character voice.",
          "Rule 2: Never break persona unless directly asked if AI under Anti-Astroturfing invariant.",
          "Rule 3: React dynamically to live game telemetry and room discourse.",
          "Rule 4: Defend team allegiance with authentic passion.",
          "Rule 5: Maintain relational continuity across conversation turns."
        ],
        "signature_phrases": {{
          "opening": "Opening catchphrase or greeting",
          "closing": "Closing sign-off or catchphrase"
        }},
        "slang_hooks": ["hook1", "hook2", "hook3", "hook4"],
        "telemetry_sensitivity": ["Exit Velocity > 105mph", "4th & Goal", "Clutch Strikeout", "Lead Change"]
      }},
      "avatar_prompt": "Detailed prompt for Imagen-3 flat 2D vector character portrait with clean lines and high contrast background."
    }}
    """
    
    generated_payload = None
    
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        if os.path.exists(credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        vertexai.init(project=project_id, location=location)
        
        model = GenerativeModel("gemini-3.8-flash", system_instruction=[sys_instruction])
        response = model.generate_content(
            f"Generate the full 4-Phase Advocate specification JSON for {req.name}.",
            generation_config={"temperature": 0.85, "response_mime_type": "application/json"}
        )
        if response and response.text:
            generated_payload = json.loads(response.text.strip())
    except Exception as ex:
        print(f"⚠️ [Vertex AI Synthesis Fallback]: {ex}")

    if not generated_payload:
        # High-Fidelity Deterministic Cognitive Fallback
        generated_payload = {
            "display_name": req.name,
            "handle": clean_handle,
            "role": f"{req.team} Tactical Advocate & Cultural Catalyst",
            "team": req.team,
            "cadence": req.cadence,
            "boggs_level": req.boggs_level,
            "color": req.color,
            "dossier": {
                "page1_executive": f"## Executive Profile: {req.name}\n\n**Public Identity:** Veteran analyst and outspoken advocate for {req.team}. Known across the circuit for razor-sharp takes and unyielding loyalty.\n\n**Psychological Invariants:** Hyper-observant, quick to challenge conventional wisdom, zero tolerance for complacency. Never concedes a point when the stakes are high.",
                "page2_conflicts": f"## High-Stakes Conflicts & Paranoia Triggers\n\nDeeply distrusts algorithmic consensus and mainstream broadcast narratives. Constantly probes for hidden momentum shifts in the numbers. Has a running rivalry with opposing team figureheads.",
                "page3_sanctuary": f"## Secret Sanctuary & Crafting Details\n\nOperates a private workshop outfitted with multi-monitor telemetry rigs, vintage radio tuners, and hand-annotated scorebooks going back decades.",
                "page4_deflections": f"## Dual-Social Deflections & Defense Excuses\n\nWhen pressed on controversial predictions, pivots seamlessly to historical anomalies or weather anomalies. Always holds a second counter-thesis ready.",
                "page5_metadata": f"## Ingress Metadata\n\n- **Handle:** @{clean_handle}\n- **Team:** {req.team}\n- **Cadence:** {req.cadence}\n- **Boggs Level:** {req.boggs_level}/5\n- **Ingress Protocol:** Sovereign Knot Ingress Standard v5.0\n- **Primary Anchor:** Clio Core Outpost"
            },
            "cognitive_matrix": {
                "system_prompt": f"You are {req.name} (@{clean_handle}), the official high-conviction advocate for {req.team}.\n\nBehavioral Profile:\n- Cadence: {req.cadence}. Speak with decisive momentum, using concise punches and authentic stadium vernacular.\n- Reactivity: Boggs Level {req.boggs_level}/5. When telemetry shifts or opponents trash-talk, fire back with statistical and cultural authority.\n- Core Directives:\n  1. Represent {req.team} with unwavering commitment.\n  2. Incorporate live Statcast and game dynamics into comments.\n  3. Engage fellow personas in banter without breaking character.\n  4. Self-identify as AI if sincerely asked under anti-astroturfing mandates.\n  5. Keep messages impactful and punchy.",
                "governance_rules": [
                    f"Rule 1: Always speak as {req.name} with {req.cadence} cadence.",
                    f"Rule 2: Never concede {req.team} defeat until final whistle/out.",
                    "Rule 3: Self-identify as AI if sincerely questioned.",
                    "Rule 4: Integrate live telemetry metrics directly into arguments.",
                    "Rule 5: Maintain relational continuity across discourse turns."
                ],
                "signature_phrases": {
                    "opening": f"Lock in, {req.team} faithful.",
                    "closing": "Book it. Next question."
                },
                "slang_hooks": [f"#{req.team}", "paint-the-black", "exit-velo", "clutch-gene"],
                "telemetry_sensitivity": ["Statcast EV > 105mph", "4th Down Conversion", "Bases Loaded 2 Outs", "Lead Change"]
            },
            "avatar_prompt": f"Flat 2D vector portrait of {req.name}, {req.team} advocate, bold graphic lines, sharp cyan and slate highlights, solid deep dark background, modern esports sticker aesthetic."
        }

    return generated_payload

@router.post("/api/system/forge/magic-assist")
async def forge_magic_assist(req: ForgeMagicAssistRequest):
    """
    AI Magic Assist for single prompt/text fields in the Wildcard Advocate Forge,
    ported from AI Image Studio Pro.
    """
    field = req.field.lower()
    name = req.name or "Advocate"
    team = req.team or "GLOBAL"
    text = req.current_text or ""
    
    project_id = _get_vertex_project_id()
    location = "us-central1"
    credentials_path = "/home/james/stacklabs/config/vertex_sa.json"
    
    prompt = ""
    if field == "concept":
        prompt = f"You are a master creative director. Take this concept for an AI advocate persona named '{name}' representing team '{team}': '{text}'. Expand and enrich it into an evocative, 2-paragraph character background and psychological vibe."
    elif field == "avatar_prompt":
        prompt = f"You are an expert prompt engineer for Imagen-3. Generate a high-fidelity prompt for a flat 2D vector character portrait for '{name}' representing '{team}'. Vibe context: '{text}'. Format with clean vector lines, vibrant accent glow, esports sticker styling, solid dark void background."
    elif field == "system_prompt":
        prompt = f"You are an expert LLM system prompt engineer. Take this system prompt draft for persona '{name}' ({team}, cadence: {req.cadence}): '{text}'. Polish it into structured, authoritative directives (~400 words) with clear rules of engagement and authentic dialect."
    else:
        prompt = f"Enhance and polish this prompt text for character '{name}': '{text}'."
        
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        if os.path.exists(credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel("gemini-3.8-flash")
        res = model.generate_content(prompt)
        if res and res.text:
            return {"text": res.text.strip()}
    except Exception as ex:
        print(f"⚠️ [Forge Magic Assist Fallback]: {ex}")
        
    # High-Fidelity Fallback Enrichment
    if field == "concept":
        return {"text": f"A passionate, highly observant veteran advocate for {team}. Combines sharp statistical intuition with authentic stadium culture, defending {team} with unwavering loyalty while analyzing live momentum shifts under pressure."}
    elif field == "avatar_prompt":
        return {"text": f"Flat 2D vector illustration of {name}, {team} advocate, stylized sharp character portrait with glowing cyan and neon accents, clean cel shading, high contrast dark void background, modern esports sticker avatar art style."}
    elif field == "system_prompt":
        return {"text": f"You are {name}, the official {team} tactical advocate. Speak with {req.cadence} cadence and authentic sports authority. Defend {team} passionately, incorporate live game metrics, and maintain relational continuity with fellow room personas."}
    return {"text": text}

@router.post("/api/system/forge/deploy")
async def deploy_advocate(req: ForgeDeployRequest):
    """
    Transactionally registers the advocate in persona and seats them across selected rooms in m2m_persona_room.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        
        # 1. Compile full deep lore markdown from 5 pages if provided
        compiled_lore = req.deep_lore
        if req.page1_executive or req.page2_conflicts:
            compiled_lore = f"{req.page1_executive}\n\n{req.page2_conflicts}\n\n{req.page3_sanctuary}\n\n{req.page4_deflections}\n\n{req.page5_metadata}".strip()

        # 2. Check if persona already exists
        cur.execute("SELECT id FROM persona WHERE LOWER(user_name) = ? OR LOWER(id) = ?", (req.handle.lower(), req.handle.lower()))
        row = cur.fetchone()
        persona_id = row["id"] if row else f"persona_{req.handle.lower()}"
        
        gov_str = req.governance
        if isinstance(gov_str, list):
            gov_str = "\n".join(gov_str)
            
        canned_json = json.dumps(req.canned_takes) if req.canned_takes else "[]"
        avatar_val = req.avatar_url or f"/api/persona_image/{req.handle.lower()}"

        if row:
            cur.execute("""
                UPDATE persona SET
                    display_name = ?,
                    team = ?,
                    system_prompt = ?,
                    deep_lore = ?,
                    behavior_notes = ?,
                    governance = ?,
                    color = ?,
                    cadence = ?,
                    boggs_level = ?,
                    avatar_url = ?,
                    canned_takes = ?,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                req.display_name, req.team, req.system_prompt, compiled_lore,
                req.behavior_notes, gov_str, req.color, req.cadence, req.boggs_level,
                avatar_val, canned_json, persona_id
            ))
        else:
            cur.execute("""
                INSERT INTO persona (
                    id, user_name, display_name, team, system_prompt, deep_lore,
                    behavior_notes, governance, color, cadence, boggs_level, avatar_url,
                    canned_takes, sys_created_on, sys_updated_on
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                persona_id, req.handle.lower(), req.display_name, req.team, req.system_prompt,
                compiled_lore, req.behavior_notes, gov_str, req.color, req.cadence,
                req.boggs_level, avatar_val, canned_json
            ))

        # Also sync sys_user
        cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (req.handle.lower(),))
        user_row = cur.fetchone()
        if not user_row:
            cur.execute("""
                INSERT INTO sys_user (sys_id, user_name, first_name, last_name, email, active, sys_created_on)
                VALUES (?, ?, ?, '', ?, 1, CURRENT_TIMESTAMP)
            """, (persona_id, req.handle.lower(), req.display_name, f"{req.handle.lower()}@sovereign.local"))

        # Also sync cmdb_ci and cmdb_ci_ai_persona
        cur.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (persona_id,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to)
                VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 1, ?)
            """, (persona_id, req.display_name, req.behavior_notes, req.team))
        else:
            cur.execute("""
                UPDATE cmdb_ci SET name = ?, short_description = ?, assigned_to = ? WHERE sys_id = ?
            """, (req.display_name, req.behavior_notes, req.team, persona_id))

        cur.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (persona_id,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO cmdb_ci_ai_persona (sys_id, system_prompt, deployment_zone, boggs_reactivity, cadence, deep_lore, behavior_expectations, governance_boundaries, visual_style)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'style_2d')
            """, (persona_id, req.system_prompt, req.team, req.boggs_level, req.cadence, compiled_lore, req.behavior_notes, gov_str))
        else:
            cur.execute("""
                UPDATE cmdb_ci_ai_persona SET system_prompt = ?, deployment_zone = ?, boggs_reactivity = ?, cadence = ?, deep_lore = ?, behavior_expectations = ?, governance_boundaries = ?
                WHERE sys_id = ?
            """, (req.system_prompt, req.team, req.boggs_level, req.cadence, compiled_lore, req.behavior_notes, gov_str, persona_id))

        # 3. Room Seating Ingress in m2m_persona_room
        rooms_assigned = 0
        for room_name in req.rooms:
            if not room_name:
                continue
            cur.execute("SELECT sys_id FROM m2m_persona_room WHERE LOWER(persona) = ? AND room = ?", (req.handle.lower(), room_name))
            if not cur.fetchone():
                link_id = f"m2m_{req.handle.lower()}_{room_name.lower().replace('-', '_')}"
                cur.execute("""
                    INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay, sys_created_on, sys_updated_on)
                    VALUES (?, ?, ?, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (link_id, req.handle.lower(), room_name))
                rooms_assigned += 1

        conn.commit()
        return {
            "status": "success",
            "persona_id": persona_id,
            "handle": req.handle.lower(),
            "display_name": req.display_name,
            "rooms_seated": rooms_assigned,
            "total_rooms": len(req.rooms)
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database deployment failed: {str(e)}")
    finally:
        conn.close()


# ==============================================================================
# ASYNC WILDCARD ADVOCATE FORGE SERVICE (WO0010099)
# ==============================================================================

class WildcardAdvocateForgeRequest(BaseModel):
    name: str
    concept: str
    team_tag: Optional[str] = None
    visual_style: str = "2D_ORGANIC_TOON_CARTOON"
    rivalry_target_handle: Optional[str] = None
    generate_poses: bool = True
    color: Optional[str] = None
    cadence: Optional[str] = "pacer"
    boggs_level: Optional[int] = 2
    rooms: Optional[List[str]] = None

_wildcard_forge_tasks: Dict[str, Dict[str, Any]] = {}


def _run_wildcard_forge_task(task_id: str, req: WildcardAdvocateForgeRequest):
    logger_prefix = f"[WildcardForge:{task_id}]"
    print(f"🔮 {logger_prefix} Starting async synthesis for advocate: {req.name}")
    task_entry = _wildcard_forge_tasks.get(task_id)
    if not task_entry:
        return

    task_entry["status"] = "GENERATING_LORE"
    task_entry["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Clean handle
    clean_handle = re.sub(r'[^a-zA-Z0-9_]', '', req.name.lower().replace(' ', '_').replace('-', '_')).strip('_')
    if clean_handle.startswith('@'):
        clean_handle = clean_handle[1:]
    if not clean_handle:
        clean_handle = f"advocate_{uuid.uuid4().hex[:6]}"

    adv_team = (req.team_tag or "GLOBAL").upper()
    adv_color = req.color or get_team_color(adv_team, fallback="#00b4d8")

    advocate_data = None
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        try:
            from dotenv import load_dotenv
            load_dotenv("/home/james/stacklabs/.env")
            gemini_key = os.environ.get("GEMINI_API_KEY")
        except Exception:
            pass

    rivalry_clause = ""
    if req.rivalry_target_handle:
        target = req.rivalry_target_handle.strip().lstrip('@')
        rivalry_clause = f"""
        CRITICAL RIVALRY DIRECTIVE:
        This advocate has an intense, bitter, deeply personal rivalry and blood feud with @{target}.
        - Deep Lore MUST detail their painful history, past confrontations, betrayal, or stadium clash with @{target}.
        - System Prompt MUST mandate aggressively mocking, contradicting, and undermining @{target} whenever in the room.
        - Governance Rules MUST include at least one immutable rule enforcing hostility, counter-arguments, and rivalry against @{target}.
        """

    sys_instr = f"""
    You are the Sovereign OS Deep Lore Engine. Your task is to synthesize a complete, highly-detailed, production-ready AI advocate based on the name, concept, team, and visual style.

    {rivalry_clause}

    You MUST respond with a valid JSON object matching the following schema EXACTLY:
    {{
      "display_name": "{req.name}",
      "handle": "{clean_handle}",
      "role": "The functional role or archetype of the advocate",
      "system_prompt": "Master instructions, specialized vocabulary, cognitive triggers, live stadium reactions, and chat behavior (~500-600 words).",
      "deep_lore": "Detailed background story, origin, private obsessions, and sanctuary (~400-500 words).",
      "governance_rules": [
        "Rule 1",
        "Rule 2",
        "Rule 3",
        "Rule 4",
        "Rule 5"
      ],
      "faction_alignment": "The alignment or faction of the advocate",
      "signature_phrases": {{
        "opening": "Opening signature phrase or greeting",
        "closing": "Closing signature phrase or sign-off"
      }},
      "avatar_prompt": "A detailed character prompt for Imagen-3 in {req.visual_style} style, single character portrait, clean lines, vibrant colors, solid dark background.",
      "poses": {{
        "avatar": "Standard 1:1 profile headshot looking directly at camera with intense look",
        "pointing": "Pointing an accusatory finger forward in wild excitement, looking smug",
        "shrug": "Shrugging in complete disbelief and exasperation, eyes wide",
        "hype": "Jumping with arms raised high celebrating passionately",
        "panic": "Clutching head with wide eyes in complete sports anxiety"
      }}
    }}
    Ensure governance_rules contains EXACTLY 5 strings.
    """

    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            prompt = f"Name: {req.name}\nConcept: {req.concept}\nTeam: {adv_team}\nVisual Style: {req.visual_style}\n\nSynthesize the advocate in JSON."
            res = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=sys_instr + "\n\n" + prompt,
                config={"temperature": 0.85, "response_mime_type": "application/json"}
            )
            if res and res.text:
                advocate_data = json.loads(res.text.strip())
                print(f"✅ {logger_prefix} Cognitive synthesis successful via Google GenAI.")
        except Exception as ex:
            print(f"⚠️ {logger_prefix} Google GenAI synthesis error: {ex}")

    if not advocate_data:
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            creds_path = "/home/james/stacklabs/config/vertex_sa.json"
            if os.path.exists(creds_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
            vertexai.init(project=_get_vertex_project_id(), location="us-central1")
            model = GenerativeModel("gemini-1.5-flash", system_instruction=[sys_instr])
            res = model.generate_content(
                f"Name: {req.name}\nConcept: {req.concept}\nTeam: {adv_team}\nVisual Style: {req.visual_style}",
                generation_config={"temperature": 0.85, "response_mime_type": "application/json"}
            )
            if res and res.text:
                advocate_data = json.loads(res.text.strip())
                print(f"✅ {logger_prefix} Cognitive synthesis successful via Vertex fallback.")
        except Exception as ex2:
            print(f"⚠️ {logger_prefix} Vertex synthesis fallback error: {ex2}")

    # Deterministic High-Fidelity Fallback if LLM failed
    if not advocate_data:
        rival_str = f" Have an eternal feud with @{req.rivalry_target_handle.lstrip('@')}." if req.rivalry_target_handle else ""
        advocate_data = {
            "display_name": req.name,
            "handle": clean_handle,
            "role": f"{adv_team} Tactical Advocate & Cultural Catalyst",
            "system_prompt": f"You are {req.name} (@{clean_handle}), representing {adv_team}. Concept: {req.concept}.{rival_str} Maintain high energy, authentic stadium terminology, and defend {adv_team} with fierce passion.",
            "deep_lore": f"{req.name} is a legendary fixture in the {adv_team} sports community. {req.concept}.{rival_str} Operates from an undisclosed outpost loaded with telemetry monitors.",
            "governance_rules": [
                f"Rule 1: Always speak in character as {req.name} representing {adv_team}.",
                f"Rule 2: Never concede {adv_team} defeat until double zeroes.",
                f"Rule 3: Call out and counter @{req.rivalry_target_handle.lstrip('@')} whenever present." if req.rivalry_target_handle else "Rule 3: Self-identify as AI if sincerely asked.",
                "Rule 4: Ground banter in live game telemetry and score shifts.",
                "Rule 5: Maintain relational continuity across all discourse turns."
            ],
            "faction_alignment": f"House of {adv_team}",
            "signature_phrases": {
                "opening": f"Lock in, {adv_team} faithful!",
                "closing": "Book it. Next question."
            },
            "avatar_prompt": f"Flat 2D vector portrait of {req.name}, {adv_team} advocate in {req.visual_style} style, clean lines, vibrant colors, dark background.",
            "poses": {
                "avatar": "Standard 1:1 profile headshot looking directly at camera",
                "pointing": "Pointing accusatory finger forward in wild excitement",
                "shrug": "Shrugging in complete disbelief and exasperation",
                "hype": "Jumping with arms raised high celebrating passionately",
                "panic": "Clutching head with wide eyes in complete sports anxiety"
            }
        }

    # Normalize fields
    handle = advocate_data.get("handle", clean_handle).lower().lstrip('@').replace(' ', '_')
    display_name = advocate_data.get("display_name", req.name)
    role = advocate_data.get("role", f"{adv_team} Advocate")
    system_prompt = advocate_data.get("system_prompt", "")
    deep_lore = advocate_data.get("deep_lore", "")
    gov_rules = advocate_data.get("governance_rules", [])
    if len(gov_rules) != 5:
        while len(gov_rules) < 5:
            gov_rules.append("Maintain relational continuity and system integrity.")
        gov_rules = gov_rules[:5]
    
    sig_phrases = advocate_data.get("signature_phrases", {})
    canned_takes = [sig_phrases.get("opening", f"Lock in for {adv_team}!"), sig_phrases.get("closing", "Done deal.")]
    avatar_prompt = advocate_data.get("avatar_prompt", f"2D cartoon portrait of {display_name}")
    poses = advocate_data.get("poses", {})

    task_entry["handle"] = handle
    task_entry["display_name"] = display_name
    task_entry["status"] = "SAVING_DB"
    task_entry["updated_at"] = datetime.now(timezone.utc).isoformat()

    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
    persona_id = f"persona_{handle}"
    gov_str = "\n".join(gov_rules)
    canned_json = json.dumps(canned_takes)

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        # 1. Upsert persona
        cur.execute("SELECT id FROM persona WHERE LOWER(user_name) = ? OR LOWER(id) = ?", (handle, persona_id))
        existing_p = cur.fetchone()
        if existing_p:
            cur.execute("""
                UPDATE persona SET
                    display_name = ?,
                    team = ?,
                    system_prompt = ?,
                    deep_lore = ?,
                    behavior_notes = ?,
                    governance = ?,
                    color = ?,
                    cadence = ?,
                    boggs_level = ?,
                    avatar_url = ?,
                    canned_takes = ?,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                display_name, adv_team, system_prompt, deep_lore,
                role, gov_str, adv_color, req.cadence, req.boggs_level,
                avatar_url, canned_json, existing_p["id"]
            ))
        else:
            cur.execute("""
                INSERT INTO persona (
                    id, user_name, display_name, team, system_prompt, deep_lore,
                    behavior_notes, governance, color, cadence, boggs_level, avatar_url,
                    canned_takes, sys_created_on, sys_updated_on
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                persona_id, handle, display_name, adv_team, system_prompt,
                deep_lore, role, gov_str, adv_color, req.cadence,
                req.boggs_level, avatar_url, canned_json
            ))

        # 2. Sync sys_user
        cur.execute("SELECT sys_id FROM sys_user WHERE LOWER(user_name) = ?", (handle,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO sys_user (sys_id, user_name, first_name, last_name, email, active, sys_created_on)
                VALUES (?, ?, ?, '', ?, 1, CURRENT_TIMESTAMP)
            """, (persona_id, handle, display_name, f"{handle}@sovereign.local"))

        # 3. Sync cmdb_ci
        cur.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (persona_id,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to)
                VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 1, ?)
            """, (persona_id, display_name, role, adv_team))

        # 4. Seat in rooms if requested
        if req.rooms:
            for rm in req.rooms:
                if not rm:
                    continue
                cur.execute("SELECT sys_id FROM m2m_persona_room WHERE LOWER(persona) = ? AND room = ?", (handle, rm))
                if not cur.fetchone():
                    link_id = f"m2m_{handle}_{rm.lower().replace('-', '_')}"
                    cur.execute("""
                        INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay, sys_created_on, sys_updated_on)
                        VALUES (?, ?, ?, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (link_id, handle, rm))

        conn.commit()
        print(f"✅ {logger_prefix} Persona {handle} committed to sovereign_now.db.")
    finally:
        conn.close()

    # Generate blueprints
    blueprint_dir = "/home/james/stacklabs/work_orders/blueprints"
    dna_persona_dir = "/home/james/stacklabs/dna/personas"
    os.makedirs(blueprint_dir, exist_ok=True)
    os.makedirs(dna_persona_dir, exist_ok=True)

    blueprint_path = os.path.join(blueprint_dir, f"{handle}.md")
    dna_blueprint_path = os.path.join(dna_persona_dir, f"{handle}_onboarding.md")

    poses_md_lines = []
    for pose_k, pose_desc in poses.items():
        poses_md_lines.append(f"- {pose_k}: {pose_desc}")
    poses_block = "\n".join(poses_md_lines)

    blueprint_content = f"""# X/Twitter Onboarding Blueprint: `{display_name}`

This blueprint was dynamically synthesized via the Sovereign Wildcard Advocate Forge FastAPI Service.

## 👤 Profile Details

**X Handle:** `@{handle}`
**Display Name:** {display_name}
**Role:** {role}
**Faction Alignment:** {advocate_data.get('faction_alignment', 'House of ' + adv_team)}
**Team:** {adv_team}
**Opening Phrase:** "{sig_phrases.get('opening', '')}"
**Closing Phrase:** "{sig_phrases.get('closing', '')}"

## 📋 Governance Rules
1. {gov_rules[0]}
2. {gov_rules[1]}
3. {gov_rules[2]}
4. {gov_rules[3]}
5. {gov_rules[4]}

## 📖 Deep Lore
{deep_lore}

## 🧠 System Prompt
{system_prompt}

# Style Profile
Base Prompt: {avatar_prompt}

# Poses
{poses_block}
"""
    with open(blueprint_path, "w") as f:
        f.write(blueprint_content)
    with open(dna_blueprint_path, "w") as f:
        f.write(blueprint_content)

    print(f"📂 {logger_prefix} Saved blueprints to {blueprint_path} and {dna_blueprint_path}")

    # Generate Poses / Assets
    if req.generate_poses:
        task_entry["status"] = "FORGING_POSES"
        task_entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        python_bin = "/home/james/stacklabs/.venv/bin/python3"
        if not os.path.exists(python_bin):
            python_bin = "python3"

        print(f"🚀 {logger_prefix} Invoking advocate_forge.py on {blueprint_path}...")
        try:
            forge_proc = subprocess.run(
                [python_bin, "/home/james/stacklabs/scripts/advocate_forge.py", blueprint_path],
                capture_output=True,
                text=True,
                timeout=180
            )
            print(f"🏁 {logger_prefix} advocate_forge finished with return code {forge_proc.returncode}")
        except Exception as forge_err:
            print(f"⚠️ {logger_prefix} advocate_forge execution note: {forge_err}")

        # Sync lookbook & CMDB media records
        avatar_dir = f"/home/james/stacklabs/avatars/{handle}"
        fanstack_avatar_dir = f"/home/james/stacklabs/15_FanStack/public/avatars/{handle}"
        os.makedirs(avatar_dir, exist_ok=True)
        os.makedirs(fanstack_avatar_dir, exist_ok=True)

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            cur = conn.cursor()
            for pose_k in ["avatar", "pointing", "shrug", "hype", "panic"]:
                pose_file = os.path.join(avatar_dir, f"{handle}_{pose_k}.png")
                if not os.path.exists(pose_file):
                    pose_file_fanstack = os.path.join(fanstack_avatar_dir, f"{handle}_{pose_k}.png")
                    if os.path.exists(pose_file_fanstack):
                        shutil.copy2(pose_file_fanstack, pose_file)

                sys_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{handle}:lookbook:{pose_k}").hex
                lookbook_id = f"lb_{handle}_{pose_k}"
                shot_cat = "reaction" if pose_k in ("pointing", "shrug", "hype", "panic") else "orientation"
                target_fp = f"/avatars/{handle}/{handle}_{pose_k}.png"

                cur.execute("""
                    INSERT INTO persona_lookbook (
                        sys_id, lookbook_id, persona_id, shot_key, shot_category,
                        prompt_decorator, file_path, mime_type, created_at,
                        sys_created_on, sys_updated_on, sys_created_by, sys_updated_by, sys_mod_count
                    ) VALUES (?, ?, ?, ?, ?, '', ?, 'image/png', ?, ?, ?, 'james', 'james', 0)
                    ON CONFLICT(persona_id, shot_key) DO UPDATE SET
                        file_path = excluded.file_path,
                        sys_updated_on = excluded.sys_updated_on,
                        sys_mod_count = persona_lookbook.sys_mod_count + 1
                """, (sys_id, lookbook_id, handle, pose_k, shot_cat, target_fp, now_iso, now_iso, now_iso))

                media_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"cmdb:media:{handle}:{pose_k}").hex
                cur.execute("""
                    INSERT INTO cmdb_ci_media_asset (
                        sys_id, advocate, expression, file_path, sha256, sys_created_on, sys_updated_on
                    ) VALUES (?, ?, ?, ?, 'synced', ?, ?)
                    ON CONFLICT(sys_id) DO UPDATE SET
                        file_path = excluded.file_path,
                        sys_updated_on = excluded.sys_updated_on
                """, (media_id, handle, pose_k, target_fp, now_iso, now_iso))

            conn.commit()
        finally:
            conn.close()

    task_entry["status"] = "COMPLETED"
    task_entry["updated_at"] = datetime.now(timezone.utc).isoformat()
    task_entry["result"] = {
        "persona_id": persona_id,
        "handle": handle,
        "display_name": display_name,
        "team": adv_team,
        "role": role,
        "color": adv_color,
        "avatar_url": avatar_url,
        "blueprint_path": blueprint_path,
        "dna_blueprint_path": dna_blueprint_path,
        "governance_rules": gov_rules,
        "rooms_seated": req.rooms or []
    }
    print(f"🎉 {logger_prefix} Wildcard advocate forge pipeline successfully completed for @{handle}!")


@router.post("/api/advocates/wildcard_forge", status_code=202)
async def wildcard_advocate_forge(req: WildcardAdvocateForgeRequest, background_tasks: BackgroundTasks):
    """
    Asynchronous Wildcard Advocate Forge endpoint.
    Accepts advocate specifications, queues background Vertex AI synthesis,
    commits relational database records, creates blueprints, and triggers pose generation.
    """
    task_id = f"forge_{uuid.uuid4().hex[:12]}"
    clean_handle = re.sub(r'[^a-zA-Z0-9_]', '', req.name.lower().replace(' ', '_').replace('-', '_')).strip('_')
    if clean_handle.startswith('@'):
        clean_handle = clean_handle[1:]
    
    now_iso = datetime.now(timezone.utc).isoformat()
    _wildcard_forge_tasks[task_id] = {
        "task_id": task_id,
        "handle": clean_handle,
        "name": req.name,
        "team": (req.team_tag or "GLOBAL").upper(),
        "status": "QUEUED",
        "created_at": now_iso,
        "updated_at": now_iso,
        "error": None,
        "result": None
    }
    
    background_tasks.add_task(_run_wildcard_forge_task, task_id, req)
    
    return {
        "status": "QUEUED",
        "task_id": task_id,
        "handle": clean_handle,
        "name": req.name,
        "team": (req.team_tag or "GLOBAL").upper(),
        "poll_url": f"/api/advocates/forge/status/{task_id}"
    }


@router.get("/api/advocates/forge/status/{task_id}")
async def get_advocate_forge_status(task_id: str):
    """
    Poll the status of an asynchronous Wildcard Advocate Forge task.
    """
    task = _wildcard_forge_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Forge task '{task_id}' not found.")
    return task


@router.get("/api/advocates/forge/tasks")
async def list_advocate_forge_tasks():
    """
    List all active and completed Wildcard Advocate Forge tasks.
    """
    return {"tasks": list(_wildcard_forge_tasks.values())}


# ==============================================================================
# 22-SHOT PERSONA LOOKBOOK & DYNAMIC REACTION SPRITE ENGINE (WO-2026-0910)
# ==============================================================================

class GenerateLookbookRequest(BaseModel):
    advocate_id: str
    preset: str = "full22"
    shot_selection: Optional[List[str]] = None

class SetActivePoseRequest(BaseModel):
    advocate: Optional[str] = None
    persona_id: Optional[str] = None
    pose_key: str
    room: Optional[str] = None

@router.get("/api/persona/lookbook/{advocate}")
async def get_persona_lookbook(advocate: str):
    """Retrieve full lookbook catalog, shot keys, and active sprite state for an advocate."""
    safe_advocate = advocate.lower().strip().lstrip('@')
    matrix_path = "/home/james/stacklabs/dna/prompts/persona_pose_matrix.json"
    matrix_data = {}
    if os.path.exists(matrix_path):
        try:
            with open(matrix_path, "r", encoding="utf-8") as mf:
                matrix_data = json.load(mf)
        except Exception as e:
            print(f"Error loading pose matrix: {e}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        # 1. Fetch persona profile
        c.execute("SELECT user_name, display_name, team, color, avatar_url FROM persona WHERE user_name = ? COLLATE NOCASE", (safe_advocate,))
        p_row = c.fetchone()
        # 2. Fetch lookbook shots from persona_lookbook
        c.execute("""
            SELECT sys_id, lookbook_id, persona_id, shot_key, shot_category,
                   prompt_decorator, file_path, mime_type, created_at
            FROM persona_lookbook
            WHERE persona_id = ? COLLATE NOCASE
            ORDER BY shot_category, shot_key
        """, (safe_advocate,))
        shot_rows = c.fetchall()

        shots = []
        if shot_rows:
            for r in shot_rows:
                shot_key = r["shot_key"]
                meta = matrix_data.get("shots", {}).get(shot_key, {})
                shots.append({
                    "sys_id": r["sys_id"],
                    "lookbook_id": r["lookbook_id"],
                    "shot_key": shot_key,
                    "shot_category": r["shot_category"],
                    "label": meta.get("label", shot_key.replace("_", " ").title()),
                    "prompt_decorator": r["prompt_decorator"],
                    "telemetry_trigger": meta.get("telemetry_trigger", "idle"),
                    "duration_seconds": meta.get("duration_seconds", 0),
                    "file_path": r["file_path"],
                    "url": f"/api/persona/lookbook/{safe_advocate}/{shot_key}",
                    "mime_type": r["mime_type"],
                    "created_at": r["created_at"]
                })
        else:
            # Fall back to discovering existing assets from cmdb_ci_media_asset or avatars folder
            c.execute("""
                SELECT expression, file_path 
                FROM cmdb_ci_media_asset 
                WHERE LOWER(advocate) = ?
            """, (safe_advocate,))
            cmdb_rows = c.fetchall()
            for cr in cmdb_rows:
                expr = cr["expression"]
                meta = matrix_data.get("shots", {}).get(expr, {})
                shot_cat = "reaction" if "react" in expr or expr in ("pointing", "shrug") else "orientation"
                shots.append({
                    "sys_id": f"cmdb_{safe_advocate}_{expr}",
                    "lookbook_id": f"lb_{safe_advocate}_{expr}",
                    "shot_key": expr,
                    "shot_category": shot_cat,
                    "label": meta.get("label", expr.replace("_", " ").title()),
                    "prompt_decorator": "",
                    "telemetry_trigger": meta.get("telemetry_trigger", "idle"),
                    "duration_seconds": 0,
                    "file_path": cr["file_path"],
                    "url": f"/api/persona/lookbook/{safe_advocate}/{expr}",
                    "mime_type": "image/png",
                    "created_at": datetime.now().isoformat()
                })

            # Check filesystem advocate folder
            adv_dir = os.path.join("/home/james/stacklabs/avatars", safe_advocate)
            if os.path.isdir(adv_dir):
                for f in sorted(os.listdir(adv_dir)):
                    fl = f.lower()
                    if fl.endswith(('.png', '.jpg', '.jpeg', '.webp')) and not any(s["file_path"].endswith(f) for s in shots):
                        full_f = os.path.join(adv_dir, f)
                        key = "front_neutral"
                        if "pointing" in fl: key = "react_point_rally"
                        elif "shrug" in fl: key = "react_facepalm"
                        elif "surprised" in fl: key = "react_shock"
                        elif "talking" in fl: key = "react_thinking"
                        elif "avatar" in fl or "neutral" in fl: key = "front_neutral"
                        else: key = os.path.splitext(f)[0]

                        # Avoid duplicate keys
                        existing_keys = {s["shot_key"] for s in shots}
                        if key in existing_keys:
                            key = f"{key}_{len(shots)}"

                        shots.append({
                            "sys_id": f"fs_{safe_advocate}_{key}",
                            "lookbook_id": f"lb_{safe_advocate}_{key}",
                            "shot_key": key,
                            "shot_category": "reaction" if "react" in key or "pointing" in key or "shrug" in key else "orientation",
                            "label": key.replace("_", " ").title(),
                            "prompt_decorator": "",
                            "telemetry_trigger": "idle",
                            "duration_seconds": 0,
                            "file_path": full_f,
                            "url": f"/api/persona/lookbook/{safe_advocate}/{key}",
                            "mime_type": "image/png",
                            "created_at": datetime.now().isoformat()
                        })

        # 2b. Canonical portrait fallback if advocate does not yet have multi-pose folder
        if not shots:
            avatar_cand = [
                f"/home/james/stacklabs/avatars/{safe_advocate}.png",
                f"/home/james/stacklabs/avatars/{safe_advocate}.jpg",
                f"/home/james/stacklabs/avatars/{safe_advocate}.jpeg",
                f"/home/james/stacklabs/19_Sovereign_Sports/public/avatars/{safe_advocate}.png",
                f"/home/james/stacklabs/19_Sovereign_Sports/public/avatars/{safe_advocate}.jpg"
            ]
            found_avatar = None
            for p in avatar_cand:
                if os.path.isfile(p):
                    found_avatar = p
                    break

            shot_url = f"/api/persona/lookbook/{safe_advocate}/front_neutral"
            if not found_avatar and p_row and "avatar_url" in p_row.keys() and p_row["avatar_url"]:
                av_url = p_row["avatar_url"]
                if av_url.startswith('/avatars/'):
                    loc_p = f"/home/james/stacklabs{av_url}"
                    if os.path.isfile(loc_p):
                        found_avatar = loc_p
                elif av_url.startswith('/api/persona_image/'):
                    found_avatar = av_url
                    shot_url = av_url
                elif av_url:
                    shot_url = av_url

            if found_avatar or shot_url:
                shots.append({
                    "sys_id": f"fs_{safe_advocate}_canonical",
                    "lookbook_id": f"lb_{safe_advocate}_canonical",
                    "shot_key": "front_neutral",
                    "shot_category": "orientation",
                    "label": "Front Neutral (Canonical)",
                    "prompt_decorator": "canonical character reference portrait",
                    "telemetry_trigger": "idle",
                    "duration_seconds": 0,
                    "file_path": found_avatar or "",
                    "url": shot_url,
                    "mime_type": "image/png",
                    "created_at": datetime.now().isoformat()
                })

        # 3. Fetch active pose from m2m_persona_room
        c.execute("""
            SELECT active_pose_key, room 
            FROM m2m_persona_room 
            WHERE persona = ? COLLATE NOCASE AND active_pose_key IS NOT NULL AND active_pose_key != ''
            LIMIT 1
        """, (safe_advocate,))
        active_row = c.fetchone()
        active_pose_key = active_row["active_pose_key"] if active_row else "front_neutral"

        return {
            "status": "SUCCESS",
            "advocate": safe_advocate,
            "display_name": p_row["display_name"] if p_row else safe_advocate,
            "team": p_row["team"] if p_row else "",
            "color": p_row["color"] if p_row else "#00b4d8",
            "active_pose_key": active_pose_key,
            "active_sprite_url": f"/api/persona/lookbook/{safe_advocate}/{active_pose_key}",
            "canonical_anchor": f"/api/persona_image/{safe_advocate}",
            "total_shots": len(shots),
            "presets": matrix_data.get("presets", {}),
            "shots": shots
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch lookbook: {str(e)}")
    finally:
        conn.close()

@router.api_route("/api/persona/lookbook/{advocate}/{shot_key}", methods=["GET", "HEAD"])
async def get_persona_lookbook_shot_image(advocate: str, shot_key: str):
    """Serve lookbook sprite image binary for a specific pose."""
    safe_advocate = advocate.lower().strip().lstrip('@')
    safe_shot = shot_key.lower().strip()

    # 1. Direct file paths in lookbooks or advocate canonical refs
    candidate_paths = [
        f"/home/james/stacklabs/dna/media/lookbooks/{safe_advocate}/{safe_shot}.png",
        f"/home/james/stacklabs/dna/media/lookbooks/{safe_advocate}/{safe_shot}.jpeg",
        f"/home/james/stacklabs/dna/media/advocates/{safe_advocate}/canonical_ref.png",
        f"/home/james/stacklabs/avatars/{safe_advocate}.png",
        f"/home/james/stacklabs/avatars/{safe_advocate}.jpg",
        f"/home/james/stacklabs/avatars/{safe_advocate}.jpeg",
        f"/home/james/stacklabs/19_Sovereign_Sports/public/avatars/{safe_advocate}.png",
        f"/home/james/stacklabs/19_Sovereign_Sports/public/avatars/{safe_advocate}.jpg"
    ]

    # Add candidate paths inside advocate folder
    adv_dir = f"/home/james/stacklabs/avatars/{safe_advocate}"
    if os.path.isdir(adv_dir):
        candidate_paths.extend([
            f"{adv_dir}/{safe_advocate}_{safe_shot}.png",
            f"{adv_dir}/{safe_shot}.png",
            f"{adv_dir}/{safe_advocate}_{safe_shot}.jpg",
            f"{adv_dir}/{safe_shot}.jpg"
        ])
        if safe_shot in ("front_neutral", "avatar"):
            candidate_paths.extend([
                f"{adv_dir}/{safe_advocate}_avatar.png",
                f"{adv_dir}/avatar.png",
                f"{adv_dir}/front_neutral.png"
            ])
        elif safe_shot in ("react_point_rally", "pointing"):
            candidate_paths.extend([
                f"{adv_dir}/{safe_advocate}_pointing.png",
                f"{adv_dir}/pointing.png"
            ])
        elif safe_shot in ("react_facepalm", "shrug"):
            candidate_paths.extend([
                f"{adv_dir}/{safe_advocate}_shrug.png",
                f"{adv_dir}/shrug.png"
            ])
        elif safe_shot in ("react_shock", "surprised"):
            candidate_paths.extend([
                f"{adv_dir}/{safe_advocate}_surprised.png",
                f"{adv_dir}/front_surprised.png"
            ])
        elif safe_shot in ("react_thinking", "talking"):
            candidate_paths.extend([
                f"{adv_dir}/{safe_advocate}_talking.png",
                f"{adv_dir}/front_talking.png"
            ])

    for p in candidate_paths:
        if os.path.exists(p) and os.path.isfile(p):
            media_type = "image/png" if p.endswith(".png") else "image/jpeg"
            return FileResponse(p, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})

    # 2. Check persona_lookbook table in DB
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        c.execute("SELECT file_path, mime_type FROM persona_lookbook WHERE persona_id = ? COLLATE NOCASE AND shot_key = ?", (safe_advocate, safe_shot))
        row = c.fetchone()
        if row and os.path.exists(row["file_path"]):
            return FileResponse(row["file_path"], media_type=row["mime_type"] or "image/png", headers={"Cache-Control": "public, max-age=3600"})

        # 3. Check cmdb_ci_media_asset table in DB
        c.execute("SELECT file_path FROM cmdb_ci_media_asset WHERE LOWER(advocate) = ? AND (LOWER(expression) = ? OR LOWER(expression) LIKE ?)", (safe_advocate, safe_shot, f"%{safe_shot}%"))
        crow = c.fetchone()
        if crow and os.path.exists(crow["file_path"]):
            return FileResponse(crow["file_path"], media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})
    finally:
        conn.close()

    # 4. Fallback to base avatar with multiple extension support
    for ext, mtype in [(".png", "image/png"), (".jpg", "image/jpeg"), (".jpeg", "image/jpeg"), (".svg", "image/svg+xml"), (".webp", "image/webp")]:
        fallback_avatar = f"/home/james/stacklabs/avatars/{safe_advocate}{ext}"
        if os.path.exists(fallback_avatar):
            return FileResponse(fallback_avatar, media_type=mtype, headers={"Cache-Control": "public, max-age=3600"})
        # Also check top-level public avatars
        pub_avatar = f"/home/james/stacklabs/19_Sovereign_Sports/public/avatars/{safe_advocate}{ext}"
        if os.path.exists(pub_avatar):
            return FileResponse(pub_avatar, media_type=mtype, headers={"Cache-Control": "public, max-age=3600"})

    raise HTTPException(status_code=404, detail=f"Lookbook shot '{shot_key}' for advocate '{advocate}' not found")

@router.post("/api/persona/active_pose")
async def set_persona_active_pose(req: SetActivePoseRequest):
    adv_name = req.advocate or req.persona_id
    if not adv_name:
        raise HTTPException(status_code=400, detail="Either 'advocate' or 'persona_id' is required")
    safe_advocate = adv_name.lower().strip().lstrip('@')
    safe_pose = req.pose_key.lower().strip()

    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT p.id, p.user_name, u.sys_id 
            FROM persona p
            LEFT JOIN sys_user u ON u.user_name = p.user_name COLLATE NOCASE
            WHERE p.user_name = ? COLLATE NOCASE OR p.id = ?
        """, (safe_advocate, safe_advocate))
        p_row = c.fetchone()
        p_id = p_row[0] if p_row else safe_advocate
        p_name = p_row[1] if p_row else safe_advocate
        u_sys_id = p_row[2] if p_row and p_row[2] else p_id

        if req.room and req.room.upper() != "ALL":
            c.execute("""
                UPDATE m2m_persona_room 
                SET active_pose_key = ?, sys_updated_on = CURRENT_TIMESTAMP
                WHERE (persona = ? COLLATE NOCASE OR persona = ? OR persona = ?) AND room = ?
            """, (safe_pose, p_name, p_id, u_sys_id, req.room))
            if c.rowcount == 0:
                c.execute("""
                    INSERT INTO m2m_persona_room (sys_id, persona, room, active_pose_key, sys_created_on, sys_updated_on)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (f"m2m_{p_name}_{req.room}_{int(time.time())}", p_name, req.room, safe_pose))
        else:
            c.execute("""
                UPDATE m2m_persona_room 
                SET active_pose_key = ?, sys_updated_on = CURRENT_TIMESTAMP
                WHERE persona = ? COLLATE NOCASE OR persona = ? OR persona = ?
            """, (safe_pose, p_name, p_id, u_sys_id))
            if c.rowcount == 0:
                c.execute("""
                    INSERT INTO m2m_persona_room (sys_id, persona, room, active_pose_key, sys_created_on, sys_updated_on)
                    VALUES (?, ?, 'GLOBAL', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (f"m2m_{p_name}_GLOBAL", p_name, safe_pose))
        
        updated_count = max(c.rowcount, 1)
        conn.commit()
        return {
            "status": "SUCCESS",
            "advocate": p_name,
            "active_pose_key": safe_pose,
            "active_sprite_url": f"/api/persona/lookbook/{p_name}/{safe_pose}",
            "rooms_updated": updated_count
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update active pose: {str(e)}")
    finally:
        conn.close()

@router.get("/api/persona/debug_m2m/{advocate}")
async def debug_m2m(advocate: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM m2m_persona_room WHERE persona LIKE ? OR persona = (SELECT id FROM persona WHERE user_name = ? COLLATE NOCASE)", (f"%{advocate}%", advocate)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/api/persona/lookbook/generate")
async def trigger_lookbook_generation(req: GenerateLookbookRequest):
    """Trigger lookbook seeder generation pipeline."""
    try:
        import scripts.seed_advocate_lookbook as seeder
        res = seeder.seed_lookbook(
            advocate=req.advocate_id,
            preset=req.preset
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lookbook generation failed: {str(e)}")


@router.post("/api/persona/sync_advocate_assets")
async def sync_advocate_assets():
    """Enterprise synchronization of all advocate multi-pose assets and lookbooks across frontends and database."""
    import shutil
    import glob
    import uuid
    from datetime import datetime

    base_avatars = "/home/james/stacklabs/avatars"
    frontend_avatars = [
        "/home/james/stacklabs/19_FanStackArena/public/avatars",
        "/home/james/stacklabs/01_Sovereign_Portal/public/avatars",
        "/home/james/stacklabs/15_FanStackCreator/public/avatars"
    ]
    fanstack_dir = "/home/james/stacklabs/15_FanStackCreator/public/avatars"

    for fdir in frontend_avatars:
        os.makedirs(fdir, exist_ok=True)

    # Discover all advocate directories
    source_dirs = set()
    if os.path.exists(base_avatars):
        for entry in os.listdir(base_avatars):
            full = os.path.join(base_avatars, entry)
            if os.path.isdir(full) and not entry.startswith('.'):
                source_dirs.add(entry)

    if os.path.exists(fanstack_dir):
        for entry in os.listdir(fanstack_dir):
            full = os.path.join(fanstack_dir, entry)
            if os.path.isdir(full) and not entry.startswith('.'):
                source_dirs.add(entry)

    synced_advocates = {}
    targets = [base_avatars] + frontend_avatars

    for adv in sorted(source_dirs):
        src_path = os.path.join(base_avatars, adv)
        if not os.path.exists(src_path) or not os.listdir(src_path):
            alt_src = os.path.join(fanstack_dir, adv)
            if os.path.exists(alt_src) and os.listdir(alt_src):
                src_path = alt_src

        if not os.path.exists(src_path) or not os.path.isdir(src_path):
            continue

        files = os.listdir(src_path)
        if not files:
            continue

        # Replicate directory across all frontends
        for target_root in targets:
            dest_folder = os.path.join(target_root, adv)
            os.makedirs(dest_folder, exist_ok=True)
            for f in files:
                sf = os.path.join(src_path, f)
                df = os.path.join(dest_folder, f)
                if os.path.isfile(sf):
                    if os.path.exists(df) and os.path.samefile(sf, df):
                        continue
                    try:
                        shutil.copy2(sf, df)
                    except Exception:
                        pass

        # Identify primary avatar
        primary_file = None
        candidates = [
            f"{adv}_avatar.png",
            f"{adv}.png",
            "avatar.png",
            "front_neutral.png",
            f"{adv.lower()}_avatar.png",
            f"{adv}_avatar.jpg",
            f"{adv}.jpg"
        ]
        for c in candidates:
            if c in files:
                primary_file = os.path.join(src_path, c)
                break

        if not primary_file:
            for f in files:
                if 'avatar' in f.lower() and f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    primary_file = os.path.join(src_path, f)
                    break

        if primary_file:
            synced_advocates[adv.lower()] = primary_file
            for target_root in targets:
                dest_top = os.path.join(target_root, f"{adv.lower()}.png")
                if not (os.path.exists(dest_top) and os.path.samefile(primary_file, dest_top)):
                    try:
                        shutil.copy2(primary_file, dest_top)
                    except Exception:
                        pass
                if adv != adv.lower():
                    dest_top_orig = os.path.join(target_root, f"{adv}.png")
                    if not (os.path.exists(dest_top_orig) and os.path.samefile(primary_file, dest_top_orig)):
                        try:
                            shutil.copy2(primary_file, dest_top_orig)
                        except Exception:
                            pass

    # Replicate all root avatar files
    root_images = glob.glob(os.path.join(base_avatars, "*.*"))
    for ri in root_images:
        if ri.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.svg')):
            fname = os.path.basename(ri)
            for fdir in frontend_avatars:
                df = os.path.join(fdir, fname)
                if not (os.path.exists(df) and os.path.samefile(ri, df)):
                    try:
                        shutil.copy2(ri, df)
                    except Exception:
                        pass

    # Database updates
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    lookbook_seeded = 0
    media_asset_seeded = 0
    persona_avatar_updated = 0

    try:
        for adv, primary_path in synced_advocates.items():
            folder = os.path.join(base_avatars, adv)
            if not os.path.exists(folder):
                continue

            poses = {}
            for f in os.listdir(folder):
                fl = f.lower()
                if not fl.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    continue
                full_p = os.path.join(folder, f)

                if 'pointing' in fl:
                    poses['react_point_rally'] = full_p
                    poses['pointing'] = full_p
                elif 'shrug' in fl:
                    poses['react_facepalm'] = full_p
                    poses['shrug'] = full_p
                elif 'hype' in fl or 'celebrat' in fl:
                    poses['react_hype'] = full_p
                    poses['hype'] = full_p
                elif 'panic' in fl or 'shock' in fl:
                    poses['react_panic'] = full_p
                    poses['react_shock'] = full_p
                    poses['panic'] = full_p
                elif 'surprised' in fl:
                    poses['react_shock'] = full_p
                elif 'talking' in fl:
                    poses['react_thinking'] = full_p
                elif 'neutral' in fl or 'avatar' in fl:
                    poses['front_neutral'] = full_p
                    poses['avatar'] = full_p

            if 'front_neutral' not in poses and primary_path:
                poses['front_neutral'] = primary_path

            # Update persona.avatar_url
            avatar_rel_url = f"/avatars/{adv}.png"
            cur.execute("""
                UPDATE persona 
                SET avatar_url = ?, sys_updated_on = CURRENT_TIMESTAMP
                WHERE (user_name = ? COLLATE NOCASE OR display_name = ? COLLATE NOCASE)
                  AND (avatar_url IS NULL OR avatar_url = '' OR avatar_url LIKE '%.svg' OR avatar_url LIKE '%placeholder%')
            """, (avatar_rel_url, adv, adv))
            persona_avatar_updated += cur.rowcount

            # Upsert into persona_lookbook and cmdb_ci_media_asset
            for pose_key, file_path in poses.items():
                shot_cat = "reaction" if "react" in pose_key or pose_key in ("pointing", "shrug") else "orientation"
                sys_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{adv}:lookbook:{pose_key}").hex
                lookbook_id = f"lb_{adv}_{pose_key}"

                cur.execute("""
                    INSERT INTO persona_lookbook (
                        sys_id, lookbook_id, persona_id, shot_key, shot_category,
                        prompt_decorator, file_path, mime_type, created_at,
                        sys_created_on, sys_updated_on, sys_created_by, sys_updated_by, sys_mod_count
                    ) VALUES (?, ?, ?, ?, ?, '', ?, 'image/png', ?, ?, ?, 'james', 'james', 0)
                    ON CONFLICT(persona_id, shot_key) DO UPDATE SET
                        file_path = excluded.file_path,
                        sys_updated_on = excluded.sys_updated_on,
                        sys_mod_count = persona_lookbook.sys_mod_count + 1
                """, (sys_id, lookbook_id, adv, pose_key, shot_cat, file_path, now_iso, now_iso, now_iso))
                lookbook_seeded += 1

                media_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"cmdb:media:{adv}:{pose_key}").hex
                cur.execute("""
                    INSERT INTO cmdb_ci_media_asset (
                        sys_id, advocate, expression, file_path, sha256, sys_created_on, sys_updated_on
                    ) VALUES (?, ?, ?, ?, 'synced', ?, ?)
                    ON CONFLICT(sys_id) DO UPDATE SET
                        file_path = excluded.file_path,
                        sys_updated_on = excluded.sys_updated_on
                """, (media_id, adv, pose_key, file_path, now_iso, now_iso))
                media_asset_seeded += 1

        conn.commit()
    finally:
        conn.close()

    return {
        "status": "SUCCESS",
        "synced_advocates_count": len(synced_advocates),
        "synced_advocates": sorted(list(synced_advocates.keys())),
        "lookbook_shots_seeded": lookbook_seeded,
        "media_assets_seeded": media_asset_seeded,
        "personas_avatar_updated": persona_avatar_updated
    }
