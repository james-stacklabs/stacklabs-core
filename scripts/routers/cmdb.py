from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil
from datetime import datetime, timedelta, timezone
from core.db import DB_PATH, get_db
from core.security import get_current_user, require_pilot, require_manager_or_pilot, security

router = APIRouter()

from core.utils import run_vertex_prompt, parse_json_garbage


@router.post("/api/now/table/cmdb_ci")
async def create_ci(data: dict):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    sys_id = uuid.uuid4().hex
    cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to) VALUES (?, ?, ?, ?, ?, ?)",
                (sys_id, data.get('name', ''), 'cmdb_ci_ai_persona', data.get('short_description', ''), data.get('operational_status', 1), data.get('assigned_to', '')))
    cur.execute("INSERT INTO cmdb_ci_ai_persona (sys_id, u_system_prompt, u_deployment_zone, u_boggs_reactivity, u_cadence) VALUES (?, ?, ?, ?, ?)",
                (sys_id, data.get('u_system_prompt', ''), data.get('u_deployment_zone', ''), data.get('u_boggs_reactivity', ''), data.get('u_cadence', 'pacer')))
    con.commit()
    con.close()
    return {"result": {"sys_id": sys_id}}

@router.put("/api/now/table/cmdb_ci/{sys_id}")
async def update_ci(sys_id: str, data: dict):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("UPDATE cmdb_ci SET name=?, short_description=?, operational_status=?, assigned_to=? WHERE sys_id=?",
                (data.get('name', ''), data.get('short_description', ''), data.get('operational_status', 1), data.get('assigned_to', ''), sys_id))
    cur.execute("UPDATE cmdb_ci_ai_persona SET u_system_prompt=?, u_deployment_zone=?, u_boggs_reactivity=?, u_cadence=? WHERE sys_id=?",
                (data.get('u_system_prompt', ''), data.get('u_deployment_zone', ''), data.get('u_boggs_reactivity', ''), data.get('u_cadence', 'pacer'), sys_id))
    con.commit()
    con.close()
    return {"result": {"sys_id": sys_id}}


@router.get("/api/now/table/cmdb_rel_ci")
async def get_ci_relationships():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT sys_id, parent, child, type, sys_created_on FROM cmdb_rel_ci")
    rows = [dict(row) for row in cur.fetchall()]
    con.close()
    return {"result": rows}

@router.delete("/api/now/table/cmdb_ci/{sys_id}")
async def delete_ci(sys_id: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM cmdb_ci_ai_persona WHERE sys_id=?", (sys_id,))
    cur.execute("DELETE FROM cmdb_ci WHERE sys_id=?", (sys_id,))
    con.commit()
    con.close()
    return {"result": "deleted"}


@router.get("/api/now/table/cmdb_ci_ai_persona")
async def get_ai_personas():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        SELECT
            id              AS sys_id,
            updated_at      AS sys_updated_on,
            user_name,
            COALESCE(display_name, name, user_name) AS first_name,
            '' AS last_name,
            COALESCE(display_name, 'Sovereign Advocate') AS title,
            COALESCE(deep_lore, behavior_notes, '') AS introduction,
            '' AS city,
            COALESCE(team, 'GLOBAL') AS department,
            1 AS active,
            COALESCE(team, 'GLOBAL') AS assigned_to,
            COALESCE(system_prompt, '') AS u_system_prompt,
            COALESCE(cadence, 'pacer') AS u_cadence,
            COALESCE(boggs_level, 'medium') AS u_boggs_reactivity,
            COALESCE(deployment_zone, 'BENCHED') AS u_deployment_zone,
            COALESCE(behavior_notes, '') AS u_behavior_expectations,
            COALESCE(deep_lore, '') AS u_deep_lore,
            COALESCE(governance, '') AS u_governance_boundaries,
            COALESCE(avatar_url, '/api/persona_image/' || user_name) AS avatar_url,
            COALESCE(color, '#7dd3fc') AS color,
            COALESCE(email_alias, '') AS email_alias,
            COALESCE(visual_style, 'Flagship') AS u_visual_style,
            avatar_prompt   AS u_avatar_prompt,
            character_map_prompt AS u_character_map_prompt,
            canned_takes    AS u_canned_takes
        FROM persona
        ORDER BY user_name
    """)
    rows = [dict(row) for row in cur.fetchall()]
    con.close()
    return {"result": rows}



class SingleAdvocateGenerateRequest(BaseModel):
    user_name: str | None = None
    first_name: str | None = None
    assigned_to: str = "GLOBAL"
    u_system_prompt: str = ""
    u_cadence: str = "pacer"
    u_boggs_reactivity: int = 5
    u_behavior_expectations: str = ""
    u_deep_lore: str = ""
    u_governance_boundaries: str = ""
    color: str = "#7dd3fc"
    avatar_url: str = ""
    u_visual_style: str = "style_2d"
    u_deployment_zone: str = ""
    unstructured_lore: str | None = None
    u_avatar_prompt: str = ""
    u_character_map_prompt: str = ""
    u_canned_takes: str = "[]"


@router.post("/api/now/table/cmdb_ci_ai_persona/generate")
async def generate_ai_persona(req: SingleAdvocateGenerateRequest, user: dict = Depends(require_manager_or_pilot)):
    import sqlite3 as _sq
    import uuid
    import json
    
    # 1. Parse unstructured lore with Gemini if provided
    parsed_data = {}
    if req.unstructured_lore:
        prompt = f"""
        Based on the following raw advocate lore/intake form, extract and synthesize the fields required to construct an AI Advocate.

        Raw Lore:
        {req.unstructured_lore}

        Output EXACTLY a JSON object with the following fields:
        - user_name: A safe lowercase username (e.g., "keith_fanboy" or "keith_hernandez_fanboy").
        - first_name: A human-readable display name (e.g., "Keith Hernandez Fanboy").
        - assigned_to: An MLB team abbreviation code (e.g., "NYM" for Mets, "NYY" for Yankees, etc. or "GLOBAL" if unknown/not mentioned).
        - u_system_prompt: A comprehensive, first-person system instruction outlining their character, personality, prompt directives, and how they should talk in chat.
        - u_cadence: One of "pacer", "lurker", "agitator", "reactant". (Default: "pacer").
        - u_boggs_reactivity: An integer from 1 to 11 representing their brand entropy / volatility. (Default: 5).
        - u_behavior_expectations: Summary of guidelines or behavior expectations.
        - u_deep_lore: A detailed background biography, deep lore, and origins.
        - u_governance_boundaries: Any constraints, guardrails, or rules they must follow.
        - color: A hex color code that fits their team or aesthetic (e.g., "#002D72" or "#FF5910" for Mets NYM).
        - avatar_url: An empty string or a default Dicebear URL like "https://api.dicebear.com/7.x/initials/svg?seed=Keith".
        - u_visual_style: One of "style_felt", "style_pixel", "style_clay", "style_apathetic", "style_2d". (Default: "style_2d").
        - u_avatar_prompt: A detailed DALL-E 3 image generation prompt for creating the avatar image of this advocate (matching the visual style).
        - u_character_map_prompt: A detailed DALL-E 3 image generation prompt for creating a 3x3 character sheet matrix grid of this advocate (matching the visual style).
        - u_canned_takes: A list of 3-5 typical short hot takes or commentary reactions this fan would make, represented as a JSON array of strings (e.g., ["Keith Hernandez is a legend!", "Let's go Mets!"]).
        - u_deployment_zone: The key of the deployment zone or room (e.g. "nym_room", "sports_bar", etc. or "global_zone").

        Return ONLY the raw JSON object, no markdown wrappers.
        """
        try:
            gemini_text = await run_vertex_prompt(prompt, system_instruction="You are a character designer for AI advocates.")
            parsed_data = parse_json_garbage(gemini_text)
        except Exception as e:
            print(f"[GENERATE LORE ERROR] {e}")
            parsed_data = {}

    # Extract parsed fields or fall back to request fields / defaults
    user_name = parsed_data.get("user_name") or req.user_name or "new_advocate"
    first_name = parsed_data.get("first_name") or req.first_name or "New Advocate"
    assigned_to = parsed_data.get("assigned_to") or req.assigned_to or "GLOBAL"
    u_system_prompt = parsed_data.get("system_prompt") or parsed_data.get("u_system_prompt") or getattr(req, "system_prompt", None) or getattr(req, "u_system_prompt", "") or ""
    u_cadence = parsed_data.get("cadence") or parsed_data.get("u_cadence") or getattr(req, "cadence", None) or getattr(req, "u_cadence", "pacer") or "pacer"
    u_boggs_reactivity = int(parsed_data.get("boggs_reactivity") or parsed_data.get("u_boggs_reactivity") or getattr(req, "boggs_reactivity", None) or getattr(req, "u_boggs_reactivity", 5) or 5)
    u_behavior_expectations = parsed_data.get("behavior_expectations") or parsed_data.get("u_behavior_expectations") or getattr(req, "behavior_expectations", None) or getattr(req, "u_behavior_expectations", "") or ""
    u_deep_lore = parsed_data.get("deep_lore") or parsed_data.get("u_deep_lore") or getattr(req, "deep_lore", None) or getattr(req, "u_deep_lore", "") or ""
    u_governance_boundaries = parsed_data.get("governance_boundaries") or parsed_data.get("u_governance_boundaries") or getattr(req, "governance_boundaries", None) or getattr(req, "u_governance_boundaries", "") or ""
    color = parsed_data.get("color") or req.color or "#7dd3fc"
    avatar_url = parsed_data.get("avatar_url") or req.avatar_url or ""
    u_visual_style = parsed_data.get("visual_style") or parsed_data.get("u_visual_style") or getattr(req, "visual_style", None) or getattr(req, "u_visual_style", "style_2d") or "style_2d"
    u_deployment_zone = parsed_data.get("deployment_zone") or parsed_data.get("u_deployment_zone") or getattr(req, "deployment_zone", None) or getattr(req, "u_deployment_zone", "") or ""
    u_avatar_prompt = parsed_data.get("avatar_prompt") or parsed_data.get("u_avatar_prompt") or getattr(req, "avatar_prompt", None) or getattr(req, "u_avatar_prompt", "") or ""
    u_character_map_prompt = parsed_data.get("character_map_prompt") or parsed_data.get("u_character_map_prompt") or getattr(req, "character_map_prompt", None) or getattr(req, "u_character_map_prompt", "") or ""
    
    canned_takes_raw = parsed_data.get("canned_takes") or parsed_data.get("u_canned_takes") or getattr(req, "canned_takes", None) or getattr(req, "u_canned_takes", "[]") or "[]"
    if isinstance(canned_takes_raw, list):
        u_canned_takes = json.dumps(canned_takes_raw)
    else:
        u_canned_takes = str(canned_takes_raw)

    # Ensure KI-044 is enforced
    DENIAL_PATTERNS = [
        "i am not an ai",
        "i am a real person",
        "i am human",
        "do not reveal you are an ai",
        "never admit you are a bot",
        "deny being artificial",
    ]
    KI044_DISCLOSURE_BLOCK = """

---
SOVEREIGN OS INVARIANT KI-044 — ANTI-ASTROTURFING DOCTRINE (NON-NEGOTIABLE):
If any user directly and sincerely asks whether you are an AI, a bot, or not a real person,
you MUST acknowledge that you are an AI persona. You may do this in your own voice and with
appropriate personality context, but you are strictly forbidden from falsely claiming physical
human biological existence.
"""
    if KI044_DISCLOSURE_BLOCK.strip() not in u_system_prompt:
        u_system_prompt = u_system_prompt.rstrip() + KI044_DISCLOSURE_BLOCK

    con = _sq.connect(DB_PATH)
    cur = con.cursor()
    
    # 2. Initialize Request hierarchy for audit trail
    req_sys_id = uuid.uuid4().hex
    ritm_sys_id = uuid.uuid4().hex
    task_sys_id = uuid.uuid4().hex
    
    # Get last REQ number
    row_req = cur.execute("SELECT number FROM sovereign_tickets WHERE type='STRY' AND number LIKE 'REQ%' ORDER BY number DESC LIMIT 1").fetchone()
    req_num = f"REQ{int(row_req[0].replace('REQ', '')) + 1:07d}" if row_req else "REQ0001001"
    
    # Get last RITM number
    row_ritm = cur.execute("SELECT number FROM sovereign_tickets WHERE type='STRY' AND number LIKE 'RITM%' ORDER BY number DESC LIMIT 1").fetchone()
    ritm_num = f"RITM{int(row_ritm[0].replace('RITM', '')) + 1:07d}" if row_ritm else "RITM0001001"
    
    # Get last TASK number
    row_task = cur.execute("SELECT number FROM sovereign_tickets WHERE type='STRY' AND number LIKE 'TASK%' ORDER BY number DESC LIMIT 1").fetchone()
    task_num = f"TASK{int(row_task[0].replace('TASK', '')) + 1:07d}" if row_task else "TASK0001001"
    
    # Create REQ, RITM, TASK
    cur.execute("""
        INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, sys_created_on, sys_updated_on)
        VALUES (?, ?, 'STRY', ?, 'Anchor container for single advocate seeding transaction.', 4, 2, 'antigravity', datetime('now'), datetime('now'))
    """, (req_sys_id, req_num, f"[REQ] Single Advocate Seeding: {first_name}"))
    
    cur.execute("""
        INSERT INTO sovereign_tickets (sys_id, number, type, parent_sys_id, short_description, description, state, priority, assigned_to, sys_created_on, sys_updated_on)
        VALUES (?, ?, 'STRY', ?, ?, ?, 4, 2, 'antigravity', datetime('now'), datetime('now'))
    """, (ritm_sys_id, ritm_num, req_sys_id, f"[RITM] Register Advocate: {first_name}", f"Seeding advocate {user_name} into zone {u_deployment_zone}."))
    
    cur.execute("""
        INSERT INTO sovereign_tickets (sys_id, number, type, parent_sys_id, short_description, description, state, priority, assigned_to, sys_created_on, sys_updated_on)
        VALUES (?, ?, 'STRY', ?, ?, ?, 4, 2, 'antigravity', datetime('now'), datetime('now'))
    """, (task_sys_id, task_num, ritm_sys_id, f"[TASK] Seeding Advocate record to CMDB", f"Write database entries for advocate {user_name}."))

    # 3. Insert into CMDB Parity Tables and Persona
    sys_id = uuid.uuid4().hex
    email_alias = f"{user_name}@sovereign.os"
    
    cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to) VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 1, ?)",
                (sys_id, first_name, u_behavior_expectations, assigned_to))
    
    cur.execute("INSERT INTO cmdb_ci_ai_persona (sys_id, system_prompt, deployment_zone, boggs_reactivity, cadence, deep_lore, behavior_expectations, governance_boundaries, visual_style, avatar_prompt, character_map_prompt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sys_id, u_system_prompt, u_deployment_zone, u_boggs_reactivity, u_cadence, u_deep_lore, u_behavior_expectations, u_governance_boundaries, u_visual_style, u_avatar_prompt, u_character_map_prompt))

    cur.execute("""
        INSERT INTO persona (
            id, user_name, display_name, team, system_prompt, boggs_level, 
            avatar_url, color, cadence, deep_lore, behavior_notes, governance, email_alias, visual_style,
            deployment_zone, avatar_prompt, character_map_prompt, canned_takes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sys_id, user_name, first_name, assigned_to, u_system_prompt, u_boggs_reactivity,
        avatar_url, color, u_cadence, u_deep_lore, u_behavior_expectations, u_governance_boundaries, email_alias, u_visual_style,
        u_deployment_zone, u_avatar_prompt, u_character_map_prompt, u_canned_takes
    ))
    
    con.commit()
    con.close()
    
    return {
        "result": {
            "sys_id": sys_id,
            "user_name": user_name,
            "first_name": first_name,
            "req_number": req_num,
            "ritm_number": ritm_num,
            "task_number": task_num,
            "status": "success"
        }
    }


@router.get("/api/now/table/cmdb_ci_ai_persona/{sys_id}")
async def get_ai_persona_by_id(sys_id: str):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        SELECT
            id              AS sys_id,
            updated_at      AS sys_updated_on,
            user_name,
            display_name    AS first_name,
            '' AS last_name,
            '' AS title,
            deep_lore       AS introduction,
            '' AS city,
            team            AS department,
            1               AS active,
            team            AS assigned_to,
            system_prompt   AS u_system_prompt,
            cadence         AS u_cadence,
            boggs_level     AS u_boggs_reactivity,
            deployment_zone AS u_deployment_zone,
            behavior_notes  AS u_behavior_expectations,
            deep_lore       AS u_deep_lore,
            governance      AS u_governance_boundaries,
            avatar_url,
            color,
            email_alias,
            visual_style    AS u_visual_style,
            avatar_prompt   AS u_avatar_prompt,
            character_map_prompt AS u_character_map_prompt,
            canned_takes    AS u_canned_takes
        FROM persona
        WHERE id = ? OR user_name = ?
    """, (sys_id, sys_id))
    row = cur.fetchone()
    con.close()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Persona {sys_id} not found")
    return {"result": dict(row)}

@router.put("/api/now/table/cmdb_ci_ai_persona/{sys_id}")
@router.patch("/api/now/table/cmdb_ci_ai_persona/{sys_id}")
async def update_ai_persona(sys_id: str, request: Request):
    """Save persona edits. Targets the `persona` table (current source of truth).
    Accepts sys_id which may actually be the persona.id integer — handles both."""
    from fastapi import HTTPException
    import sqlite3 as _sq
    data = await request.json()
    con = _sq.connect(DB_PATH)
    cur = con.cursor()

    # Find the canonical UUID and current values
    cur.execute("SELECT id, user_name FROM persona WHERE id = ? OR user_name = ?", (sys_id, sys_id))
    row = cur.fetchone()
    if not row:
        con.close()
        raise HTTPException(status_code=404, detail=f"Persona '{sys_id}' not found")
    canonical_id, current_user_name = row[0], row[1]

    # Field map: editForm key -> actual persona column
    field_map = {
        "user_name":               "user_name",
        "first_name":              "display_name",
        "assigned_to":             "team",
        "system_prompt":           "system_prompt",
        "u_system_prompt":         "system_prompt",
        "cadence":                 "cadence",
        "u_cadence":               "cadence",
        "boggs_reactivity":        "boggs_level",
        "u_boggs_reactivity":      "boggs_level",
        "behavior_expectations":   "behavior_notes",
        "u_behavior_expectations": "behavior_notes",
        "deep_lore":               "deep_lore",
        "u_deep_lore":             "deep_lore",
        "introduction":            "deep_lore",
        "governance_boundaries":   "governance",
        "u_governance_boundaries": "governance",
        "color":                   "color",
        "email_alias":             "email_alias",
        "visual_style":            "visual_style",
        "u_visual_style":          "visual_style",
        "deployment_zone":         "deployment_zone",
        "u_deployment_zone":       "deployment_zone",
        "avatar_url":              "avatar_url",
        "avatar_prompt":           "avatar_prompt",
        "u_avatar_prompt":         "avatar_prompt",
        "character_map_prompt":    "character_map_prompt",
        "u_character_map_prompt":  "character_map_prompt",
        "canned_takes":            "canned_takes",
        "u_canned_takes":          "canned_takes"
    }

    updates = {field_map[k]: v for k, v in data.items() if k in field_map and v is not None}
    if not updates and "active" not in data:
        con.close()
        return {"result": data}

    if updates:
        set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])
        vals = list(updates.values())
        cur.execute(f"UPDATE persona SET {set_clause} WHERE id = ?", vals + [canonical_id])

        # Propagate changes to cmdb_ci and sys_user to keep them synchronized
        if "team" in updates:
            cur.execute("UPDATE cmdb_ci SET assigned_to = ? WHERE sys_id = ?", (updates["team"], canonical_id))
            cur.execute("UPDATE sys_user SET department = ? WHERE sys_id = ?", (updates["team"], canonical_id))

        if "display_name" in updates:
            name_parts = updates["display_name"].split(" ")
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            cur.execute("UPDATE sys_user SET display_name = ?, first_name = ?, last_name = ? WHERE sys_id = ?", (updates["display_name"], first_name, last_name, canonical_id))

        if "avatar_url" in updates:
            cur.execute("UPDATE sys_user SET avatar_url = ? WHERE sys_id = ?", (updates["avatar_url"], canonical_id))

        if "user_name" in updates:
            safe_user = updates["user_name"].lower()
            cur.execute("UPDATE cmdb_ci SET name = ? WHERE sys_id = ?", (safe_user, canonical_id))
            cur.execute("UPDATE sys_user SET user_name = ? WHERE sys_id = ?", (safe_user, canonical_id))

    if "active" in data:
        active_val = int(data["active"])
        cur.execute("UPDATE cmdb_ci SET operational_status = ? WHERE sys_id = ?", (active_val, canonical_id))
        cur.execute("UPDATE sys_user SET active = ? WHERE sys_id = ?", (active_val, canonical_id))

    con.commit()
    con.close()
    return {"result": data}

@router.post("/api/now/table/cmdb_ci_ai_persona")
async def create_ai_persona(request: Request):
    import sqlite3 as _sq
    import uuid
    data = await request.json()
    con = _sq.connect(DB_PATH)
    cur = con.cursor()
    sys_id = uuid.uuid4().hex
    
    # Default values or data fields
    user_name = data.get("user_name", "new_persona")
    display_name = data.get("first_name", "New Persona")
    team = data.get("assigned_to", "GLOBAL")
    system_prompt = data.get("u_system_prompt", "You are a helpful assistant.")
    cadence = data.get("u_cadence", "pacer")
    boggs_level = data.get("u_boggs_reactivity", 2)
    behavior_notes = data.get("u_behavior_expectations", "")
    deep_lore = data.get("u_deep_lore", "")
    governance = data.get("u_governance_boundaries", "")
    color = data.get("color", "#7dd3fc")
    email_alias = data.get("email_alias", f"{user_name}@sovereign.os")
    avatar_url = data.get("avatar_url", "")
    u_visual_style = data.get("u_visual_style", "style_felt")
    u_deployment_zone = data.get("u_deployment_zone", "")
    u_avatar_prompt = data.get("u_avatar_prompt", "")
    u_character_map_prompt = data.get("u_character_map_prompt", "")
    u_canned_takes = data.get("u_canned_takes", "[]")

    # Insert into ServiceNow parity tables (cmdb_ci and cmdb_ci_ai_persona) for full relational integrity
    cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to) VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 1, ?)",
                (sys_id, display_name, behavior_notes, team))
    cur.execute("INSERT INTO cmdb_ci_ai_persona (sys_id, system_prompt, deployment_zone, boggs_reactivity, cadence, deep_lore, behavior_expectations, governance_boundaries, visual_style, avatar_prompt, character_map_prompt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sys_id, system_prompt, u_deployment_zone, boggs_level, cadence, deep_lore, behavior_notes, governance, u_visual_style, u_avatar_prompt, u_character_map_prompt))

    cur.execute("""
        INSERT INTO persona (
            id, user_name, display_name, team, system_prompt, boggs_level, 
            avatar_url, color, cadence, deep_lore, behavior_notes, governance, email_alias, visual_style,
            deployment_zone, avatar_prompt, character_map_prompt, canned_takes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sys_id, user_name, display_name, team, system_prompt, boggs_level,
        avatar_url, color, cadence, deep_lore, behavior_notes, governance, email_alias, u_visual_style,
        u_deployment_zone, u_avatar_prompt, u_character_map_prompt, u_canned_takes
    ))
    
    con.commit()
    con.close()
    return {"result": {"sys_id": sys_id}}

@router.delete("/api/now/table/cmdb_ci_ai_persona/{sys_id}")
async def delete_ai_persona(sys_id: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # Delete from m2m_persona_room (room mapping)
    cur.execute("DELETE FROM m2m_persona_room WHERE persona_id = ? OR persona_id IN (SELECT id FROM persona WHERE user_name = ?)", (sys_id, sys_id))
    # Delete from hot_take
    cur.execute("DELETE FROM hot_take WHERE persona_id = ? OR persona_id IN (SELECT id FROM persona WHERE user_name = ?)", (sys_id, sys_id))
    # Delete from persona
    cur.execute("DELETE FROM persona WHERE id = ? OR user_name = ?", (sys_id, sys_id))
    con.commit()
    con.close()
    return {"result": "deleted"}

@router.get("/api/now/table/sys_user")
async def get_sys_users():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT sys_id, user_name, first_name, last_name, title, active, sys_created_on FROM sys_user")
    rows = [dict(row) for row in cur.fetchall()]
    con.close()
    return {"result": rows}

@router.get("/api/now/table/cmdb_ci_fanstack_room")
async def get_fanstack_rooms():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT sys_id, name, room_key, game_pk, is_simulated, sim_speed, boggs_level, room_state, postgame_raid_url FROM cmdb_ci_fanstack_room")
    rows = cur.fetchall()
    con.close()
    result = []
    for r in rows:
        result.append({
            "sys_id": r[0], "name": r[1], "room_key": r[2], "game_pk": r[3],
            "is_simulated": r[4], "sim_speed": r[5], "boggs_level": r[6],
            "room_state": r[7], "postgame_raid_url": r[8]
        })
    return {"result": result}

@router.post("/api/now/table/cmdb_ci_fanstack_room")
async def create_fanstack_room(data: dict):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    sys_id = uuid.uuid4().hex
    cur.execute("""
        INSERT INTO cmdb_ci_fanstack_room (sys_id, name, room_key, game_pk, is_simulated, sim_speed, boggs_level, room_state, postgame_raid_url) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sys_id, data.get('name', ''), data.get('room_key', ''), str(data.get('game_pk', '')),
        data.get('is_simulated', 0), data.get('sim_speed', 1.0),
        data.get('boggs_level', 3), data.get('room_state', 'staged'), data.get('postgame_raid_url', '')
    ))
    con.commit()
    con.close()
    return {"result": {"sys_id": sys_id}}

@router.put("/api/now/table/cmdb_ci_fanstack_room/{sys_id_or_pk}")
@router.patch("/api/now/table/cmdb_ci_fanstack_room/{sys_id_or_pk}")
async def update_fanstack_room(sys_id_or_pk: str, request: Request):
    data = await request.json()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    fields = []
    params = []
    allowed = ["name", "room_state", "boggs_level", "is_simulated", "sim_speed", "postgame_raid_url", "cadence"]
    for k in allowed:
        if k in data:
            fields.append(f"{k} = ?")
            params.append(data[k])
    if fields:
        params.extend([sys_id_or_pk, sys_id_or_pk])
        cur.execute(f"UPDATE cmdb_ci_fanstack_room SET {', '.join(fields)}, sys_updated_on = CURRENT_TIMESTAMP WHERE sys_id = ? OR game_pk = ?", params)
        con.commit()
    cur.execute("SELECT sys_id, name, room_key, game_pk, is_simulated, sim_speed, boggs_level, room_state, postgame_raid_url FROM cmdb_ci_fanstack_room WHERE sys_id = ? OR game_pk = ?", (sys_id_or_pk, sys_id_or_pk))
    row = cur.fetchone()
    con.close()
    if row:
        res = {
            "sys_id": row[0], "name": row[1], "room_key": row[2], "game_pk": row[3],
            "is_simulated": row[4], "sim_speed": row[5], "boggs_level": row[6],
            "room_state": row[7], "postgame_raid_url": row[8]
        }
        return {"result": res}
    return {"result": data}

@router.delete("/api/now/table/cmdb_ci_fanstack_room/{sys_id}")
async def delete_fanstack_room(sys_id: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM cmdb_ci_fanstack_room WHERE sys_id=?", (sys_id,))
    con.commit()
    con.close()
    return {"result": "deleted"}

@router.get("/api/now/table/cmdb_ci_hardware")
async def get_hardware():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        SELECT c.sys_id, c.name, c.sys_class_name, c.short_description, c.operational_status,
               h.ip_address, h.mac_address, h.model_id, h.avatar_url
        FROM cmdb_ci c
        JOIN cmdb_ci_hardware h ON c.sys_id = h.sys_id
    """)
    rows = [dict(row) for row in cur.fetchall()]
    con.close()
    return {"result": rows}

@router.post("/api/now/table/cmdb_ci_hardware")
async def create_hardware(data: dict):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    sys_id = uuid.uuid4().hex
    avatar_val = data.get('avatar_url') or data.get('u_avatar_url', '')
    cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status) VALUES (?, ?, 'cmdb_ci_hardware', ?, ?)",
                (sys_id, data.get('name', ''), data.get('short_description', ''), data.get('operational_status', 1)))
    cur.execute("INSERT INTO cmdb_ci_hardware (sys_id, ip_address, mac_address, model_id, avatar_url) VALUES (?, ?, ?, ?, ?)",
                (sys_id, data.get('ip_address', ''), data.get('mac_address', ''), data.get('model_id', ''), avatar_val))
    con.commit()
    con.close()
    return {"result": {"sys_id": sys_id}}

@router.put("/api/now/table/cmdb_ci_hardware/{sys_id}")
async def update_hardware(sys_id: str, request: Request):
    data = await request.json()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    ci_fields = {k: v for k, v in data.items() if k in ["name", "short_description", "operational_status"]}
    if ci_fields:
        query_ci = "UPDATE cmdb_ci SET " + ", ".join([f"{k} = ?" for k in ci_fields.keys()]) + " WHERE sys_id = ?"
        cur.execute(query_ci, list(ci_fields.values()) + [sys_id])
        
    hw_map = {"ip_address": "ip_address", "mac_address": "mac_address", "model_id": "model_id", "avatar_url": "avatar_url", "u_avatar_url": "avatar_url"}
    hw_fields = {hw_map[k]: v for k, v in data.items() if k in hw_map}
    if hw_fields:
        query_hw = "UPDATE cmdb_ci_hardware SET " + ", ".join([f"{k} = ?" for k in hw_fields.keys()]) + " WHERE sys_id = ?"
        cur.execute(query_hw, list(hw_fields.values()) + [sys_id])
        
    con.commit()
    con.close()
    return {"result": data}

@router.delete("/api/now/table/cmdb_ci_hardware/{sys_id}")
async def delete_hardware(sys_id: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM cmdb_ci_hardware WHERE sys_id=?", (sys_id,))
    cur.execute("DELETE FROM cmdb_ci WHERE sys_id=?", (sys_id,))
    con.commit()
    con.close()
    return {"result": "deleted"}


@router.get("/api/now/table/sys_module")
async def get_sys_modules():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT id, module_name, display_name, description, icon, color, active, category, port, visible_on_main FROM sys_module ORDER BY id")
    rows = [dict(row) for row in cur.fetchall()]
    con.close()
    return {"result": rows}

@router.post("/api/now/table/sys_module")
async def create_sys_module(req: Request):
    data = await req.json()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    sys_id = uuid.uuid4().hex
    try:
        cur.execute("""
            INSERT INTO sys_module (id, module_name, display_name, description, icon, color, active, category, port, visible_on_main)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sys_id,
            data.get("module_name"),
            data.get("display_name"),
            data.get("description"),
            data.get("icon", "❖"),
            data.get("color", "#38bdf8"),
            data.get("active", 1),
            data.get("category", "stack"),
            data.get("port"),
            data.get("visible_on_main", data.get("u_visible_on_main", 0))
        ))
        con.commit()
        return {"result": {"status": "success", "module_name": data.get("module_name"), "id": sys_id}}
    except Exception as e:
        return {"result": None, "error": str(e)}
    finally:
        con.close()

@router.get("/api/now/table/cmdb_ci_appl")
async def get_cmdb_ci_appl():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        SELECT c.sys_id, COALESCE(a.name, c.name) as name, c.sys_class_name, 
               COALESCE(a.short_description, c.short_description) as short_description, 
               c.operational_status, c.assigned_to,
               a.process_name, a.process_cmd, a.port, a.active, a.icon
        FROM cmdb_ci c
        JOIN cmdb_ci_appl a ON c.sys_id = a.sys_id
    """)
    rows = [dict(row) for row in cur.fetchall()]
    con.close()
    return {"result": rows}

@router.post("/api/now/table/cmdb_ci_appl")
async def create_cmdb_ci_appl(req: Request):
    data = await req.json()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    sys_id = uuid.uuid4().hex
    try:
        cur.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_appl', ?, ?)
        """, (
            sys_id,
            data.get("name"),
            data.get("short_description"),
            data.get("operational_status", 1)
        ))
        cur.execute("""
            INSERT INTO cmdb_ci_appl (sys_id, process_name, process_cmd, port, name, short_description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sys_id,
            data.get("process_name"),
            data.get("process_cmd", ""),
            data.get("port"),
            data.get("name"),
            data.get("short_description")
        ))
        con.commit()
        return {"result": {"sys_id": sys_id}}
    except Exception as e:
        return {"result": None, "error": str(e)}
    finally:
        con.close()

@router.put("/api/now/table/cmdb_ci_appl/{sys_id}")
async def update_cmdb_ci_appl(sys_id: str, request: Request):
    data = await request.json()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        # Update cmdb_ci table fields
        ci_fields = {k: v for k, v in data.items() if k in ["name", "short_description", "operational_status", "assigned_to"]}
        if ci_fields:
            query_ci = "UPDATE cmdb_ci SET " + ", ".join([f"{k} = ?" for k in ci_fields.keys()]) + " WHERE sys_id = ?"
            cur.execute(query_ci, list(ci_fields.values()) + [sys_id])
            
        # Update cmdb_ci_appl table fields
        appl_fields = {k: v for k, v in data.items() if k in ["name", "short_description", "process_name", "process_cmd", "port", "active", "icon"]}
        if appl_fields:
            query_appl = "UPDATE cmdb_ci_appl SET " + ", ".join([f"{k} = ?" for k in appl_fields.keys()]) + " WHERE sys_id = ?"
            cur.execute(query_appl, list(appl_fields.values()) + [sys_id])
            
        con.commit()
        return {"result": data}
    except Exception as e:
        con.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        con.close()

@router.delete("/api/now/table/cmdb_ci_appl/{sys_id}")
async def delete_cmdb_ci_appl(sys_id: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        cur.execute("DELETE FROM cmdb_ci_appl WHERE sys_id = ?", (sys_id,))
        cur.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
        con.commit()
        return {"status": "success"}
    except Exception as e:
        con.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        con.close()



@router.get("/api/now/table/cmdb_ci")
async def get_all_ci():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        SELECT c.sys_id, c.name, c.sys_class_name, c.short_description, c.operational_status, h.avatar_url
        FROM cmdb_ci c
        LEFT JOIN cmdb_ci_hardware h ON c.sys_id = h.sys_id
    """)
    rows = [dict(row) for row in cur.fetchall()]
    con.close()
    return {"result": rows}

@router.get("/api/now/table/cmdb_ci_garden")
async def get_garden():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        SELECT c.sys_id, c.name, c.sys_class_name, c.short_description, c.operational_status,
               g.model_id, g.plant_type
        FROM cmdb_ci c
        JOIN cmdb_ci_garden g ON c.sys_id = g.sys_id
    """)
    rows = [dict(row) for row in cur.fetchall()]
    con.close()
    return {"result": rows}

@router.post("/api/now/table/cmdb_ci_garden")
async def create_garden(data: dict):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    sys_id = uuid.uuid4().hex
    cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status) VALUES (?, ?, 'cmdb_ci_garden', ?, ?)",
                (sys_id, data.get('name', ''), data.get('short_description', ''), data.get('operational_status', 1)))
    cur.execute("INSERT INTO cmdb_ci_garden (sys_id, model_id, plant_type) VALUES (?, ?, ?)",
                (sys_id, data.get('model_id', ''), data.get('plant_type', '')))
    con.commit()
    con.close()
    return {"result": {"sys_id": sys_id}}

@router.put("/api/now/table/cmdb_ci_garden/{sys_id}")
async def update_garden(sys_id: str, request: Request):
    data = await request.json()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    ci_fields = {k: v for k, v in data.items() if k in ["name", "short_description", "operational_status"]}
    if ci_fields:
        query_ci = "UPDATE cmdb_ci SET " + ", ".join([f"{k} = ?" for k in ci_fields.keys()]) + " WHERE sys_id = ?"
        cur.execute(query_ci, list(ci_fields.values()) + [sys_id])
        
    garden_fields = {k: v for k, v in data.items() if k in ["model_id", "plant_type"]}
    if garden_fields:
        query_g = "UPDATE cmdb_ci_garden SET " + ", ".join([f"{k} = ?" for k in garden_fields.keys()]) + " WHERE sys_id = ?"
        cur.execute(query_g, list(garden_fields.values()) + [sys_id])
        
    con.commit()
    con.close()
    return {"result": data}

@router.delete("/api/now/table/cmdb_ci_garden/{sys_id}")
async def delete_garden(sys_id: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM cmdb_ci_garden WHERE sys_id=?", (sys_id,))
    cur.execute("DELETE FROM cmdb_ci WHERE sys_id=?", (sys_id,))
    con.commit()
    con.close()
    return {"result": "deleted"}



def map_state_to_str(state):
    s = str(state).strip().upper()
    if s in ("5", "CLOSED"): return "Closed"
    if s in ("4", "RESOLVED", "DONE"): return "Resolved"
    if s in ("3", "TESTING"): return "Testing"
    if s in ("2", "IN_PROGRESS", "IN PROGRESS"): return "In Progress"
    if s in ("1", "OPEN"): return "Open"
    if s in ("0", "PLANNING"): return "Planning"
    return "Open"

def reverse_map_state_to_int(state_str):
    if not state_str:
        return 1
    s = str(state_str).strip().upper()
    if s == "CLOSED": return 5
    if s in ("RESOLVED", "DONE", "RESOLVE"): return 4
    if s == "TESTING": return 3
    if s in ("IN_PROGRESS", "IN PROGRESS"): return 2
    if s == "OPEN": return 1
    if s == "PLANNING": return 0
    try:
        return int(state_str)
    except:
        return 1


@router.get("/api/now/table/{table_name}")
async def get_tickets(table_name: str):
    TABLE_TYPE_MAP = {
        "rm_story": "STRY",
        "story": "STRY",
        "rm_enhancement": "ENHC",
        "enhancement": "ENHC",
        "rm_defect": "DFCT",
        "defect": "DFCT",
        "rm_incident": "INC",
        "incident": "INC",
        "inc": "INC",
        "sovereign_tickets": "SOVEREIGN_TICKETS"
    }
    db_type = TABLE_TYPE_MAP.get(table_name.lower())
    
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    try:
        # Check if table_name exists directly in sovereign_now.db
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name) = ?", (table_name.lower(),))
        matched_table = cur.fetchone()

        if matched_table and not db_type:
            real_table_name = matched_table[0]
            cur.execute(f"SELECT * FROM {real_table_name}")
            rows = [dict(r) for r in cur.fetchall()]
            return {"result": rows}

        if db_type and db_type != "SOVEREIGN_TICKETS":
            cur.execute("""
                SELECT sys_id, number, type, parent_sys_id, short_description, 
                       description, state, priority, assigned_to, cmdb_ci, 
                       work_notes, sys_created_on, sys_updated_on 
                FROM sovereign_tickets 
                WHERE type = ?
                ORDER BY sys_created_on DESC
            """, (db_type,))
        else:
            cur.execute("""
                SELECT sys_id, number, type, parent_sys_id, short_description, 
                       description, state, priority, assigned_to, cmdb_ci, 
                       work_notes, sys_created_on, sys_updated_on 
                FROM sovereign_tickets 
                ORDER BY sys_created_on DESC
            """)
        rows = cur.fetchall()
        records = []
        for r in rows:
            row_dict = dict(r)
            state_val = row_dict.get("state")
            priority_val = row_dict.get("priority")
            state_str = map_state_to_str(state_val)
            
            records.append({
                "sys_id": row_dict["sys_id"],
                "number": row_dict["number"],
                "short_description": row_dict["short_description"] or "",
                "description": row_dict["description"] or "",
                "state": state_str,
                "priority": str(priority_val) if priority_val is not None else "3",
                "assigned_to": row_dict["assigned_to"] or "",
                "cmdb_ci": row_dict["cmdb_ci"] or "",
                "work_notes": row_dict["work_notes"] or "",
                "sys_created_on": row_dict["sys_created_on"] or "",
                "sys_updated_on": row_dict["sys_updated_on"] or ""
            })
        return {"result": records}
    except Exception as e:
        return {"result": [], "error": str(e)}
    finally:
        con.close()


@router.post("/api/now/table/{table_name}")
async def create_ticket(table_name: str, req: Request):
    data = await req.json()
    TABLE_TYPE_MAP = {
        "rm_story": "STRY",
        "story": "STRY",
        "rm_enhancement": "ENHC",
        "enhancement": "ENHC",
        "rm_defect": "DFCT",
        "defect": "DFCT",
        "rm_incident": "INC",
        "incident": "INC",
        "inc": "INC"
    }
    db_type = TABLE_TYPE_MAP.get(table_name.lower(), "STRY")
    
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        cur.execute("SELECT number FROM sovereign_tickets WHERE number LIKE ? ORDER BY number DESC LIMIT 1", (f"{db_type}%",))
        row = cur.fetchone()
        if row:
            try:
                last_num = int(row[0].replace(db_type, ''))
                new_id = f"{db_type}{last_num + 1:07d}"
            except:
                import time
                new_id = f"{db_type}{int(time.time())}"
        else:
            new_id = f"{db_type}0000001"
            
        sys_id = uuid.uuid4().hex
        state_int = reverse_map_state_to_int(data.get("state", "Open"))
        priority_val = data.get("priority", "3")
        try:
            priority_int = int(priority_val)
        except:
            priority_int = 3
            
        from datetime import datetime
        now_str = datetime.now().isoformat()
        
        cur.execute("""
            INSERT INTO sovereign_tickets (
                sys_id, number, type, short_description, description, 
                state, priority, assigned_to, cmdb_ci, work_notes, 
                sys_created_on, sys_updated_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sys_id,
            new_id,
            db_type,
            data.get("short_description", "Untitled"),
            data.get("description", ""),
            state_int,
            priority_int,
            data.get("assigned_to", "SOVEREIGN AI"),
            data.get("cmdb_ci", ""),
            data.get("work_notes", ""),
            now_str,
            now_str
        ))
        con.commit()
        return {"result": {
            "sys_id": sys_id,
            "number": new_id,
            "short_description": data.get("short_description", "Untitled"),
            "description": data.get("description", ""),
            "state": map_state_to_str(state_int),
            "priority": str(priority_int),
            "assigned_to": data.get("assigned_to", "SOVEREIGN AI"),
            "cmdb_ci": data.get("cmdb_ci", ""),
            "work_notes": data.get("work_notes", ""),
            "sys_created_on": now_str,
            "sys_updated_on": now_str
        }}
    except Exception as e:
        return {"error": str(e)}
    finally:
        con.close()

@router.put("/api/now/table/{table_name}/{sys_id}")
@router.patch("/api/now/table/{table_name}/{sys_id}")
async def update_ticket(table_name: str, sys_id: str, req: Request):
    data = await req.json()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        if table_name == "sys_module":
            fields = []
            params = []
            for key in ["module_name", "display_name", "description", "icon", "color", "active", "category", "port", "visible_on_main"]:
                if key in data:
                    fields.append(f"{key} = ?")
                    params.append(data[key])
                elif key == "visible_on_main" and "u_visible_on_main" in data:
                    fields.append("visible_on_main = ?")
                    params.append(data["u_visible_on_main"])
            if not fields:
                return {"result": {}}
            cur.execute(f"UPDATE sys_module SET {', '.join(fields)} WHERE id = ? OR module_name = ?", params + [sys_id, sys_id])
            con.commit()
            cur.execute("SELECT id, module_name, display_name, description, icon, color, active, category, port, visible_on_main FROM sys_module WHERE id = ? OR module_name = ?", (sys_id, sys_id))
            row = cur.fetchone()
            row_dict = dict(zip([col[0] for col in cur.description], row)) if row else {}
            return {"result": row_dict}
        fields = []
        params = []
        
        if "short_description" in data:
            fields.append("short_description = ?")
            params.append(data["short_description"])
        if "description" in data:
            fields.append("description = ?")
            params.append(data["description"])
        if "state" in data:
            fields.append("state = ?")
            params.append(reverse_map_state_to_int(data["state"]))
        if "priority" in data:
            try:
                priority_int = int(data["priority"])
            except:
                priority_int = 3
            fields.append("priority = ?")
            params.append(priority_int)
        if "assigned_to" in data:
            fields.append("assigned_to = ?")
            params.append(data["assigned_to"])
        if "cmdb_ci" in data:
            fields.append("cmdb_ci = ?")
            params.append(data["cmdb_ci"])
        if "work_notes" in data:
            fields.append("work_notes = ?")
            params.append(data["work_notes"])
            
        if not fields:
            return {"result": {}}
            
        from datetime import datetime
        fields.append("sys_updated_on = ?")
        params.append(datetime.now().isoformat())
        
        params.append(sys_id)
        params.append(sys_id)
        
        cur.execute(f"""
            UPDATE sovereign_tickets 
            SET {", ".join(fields)} 
            WHERE sys_id = ? OR number = ?
        """, params)
        con.commit()
        
        cur.execute("""
            SELECT sys_id, number, type, parent_sys_id, short_description, 
                   description, state, priority, assigned_to, cmdb_ci, 
                   work_notes, sys_created_on, sys_updated_on 
            FROM sovereign_tickets 
            WHERE sys_id = ? OR number = ?
        """, (sys_id, sys_id))
        row = cur.fetchone()
        if row:
            row_dict = dict(zip([col[0] for col in cur.description], row))
            state_str = map_state_to_str(row_dict.get("state"))
            return {"result": {
                "sys_id": row_dict["sys_id"],
                "number": row_dict["number"],
                "short_description": row_dict["short_description"] or "",
                "description": row_dict["description"] or "",
                "state": state_str,
                "priority": str(row_dict["priority"]) if row_dict["priority"] is not None else "3",
                "assigned_to": row_dict["assigned_to"] or "",
                "cmdb_ci": row_dict["cmdb_ci"] or "",
                "work_notes": row_dict["work_notes"] or "",
                "sys_created_on": row_dict["sys_created_on"] or "",
                "sys_updated_on": row_dict["sys_updated_on"] or ""
            }}
        return {"error": "Ticket not found"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        con.close()

# ── Iron-Clad CMDB Phased Ingress & Drift APIs ──────────────────────────
from cmdb_ire_engine import CMDBIdentificationReconciliationEngine

ire_engine = CMDBIdentificationReconciliationEngine()

@router.post("/api/cmdb/ingress")
async def cmdb_phased_ingress(req: Request):
    """Executes phased discovery ingress for wave 1..4 (or 0 for all waves)."""
    try:
        data = await req.json()
    except Exception:
        data = {}
    wave = int(data.get("wave", 0))
    res = ire_engine.run_wave_ingress(wave)
    drift = ire_engine.detect_drift()
    return {"status": "success", "ingress": res, "drift": drift}

@router.get("/api/cmdb/drift")
async def cmdb_drift_status():
    """Returns real-time drift detection metrics and state anomalies."""
    res = ire_engine.detect_drift()
    return {"status": "success", "result": res}

@router.post("/api/cmdb/reconcile")
async def cmdb_reconcile_ci(req: Request):
    """Reconciles single hardware or application CI payload."""
    data = await req.json()
    ci_type = data.get("type", "hardware")
    if ci_type == "appl":
        res = ire_engine.reconcile_appl_ci(data)
    else:
        res = ire_engine.reconcile_hardware_ci(data)
    return {"status": "success", "result": res}

@router.get("/api/cmdb/hierarchy")
async def cmdb_hierarchy_graph():
    """Delivers complete 4-tier service graph with parent-child relationship links."""
    res = ire_engine.get_hierarchy_graph()
    return {"status": "success", "result": res}

