#!/usr/bin/env python3
"""
Sovereign SDLC Portal — Core Ticketing, Sprint, and Backlog Router
Port: 8095 | Governing Standard: Invariant 50
"""

import os
import sys
import re
import json
import uuid
import time
import glob
import fcntl
import urllib.parse
import sqlite3
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from fastapi import APIRouter, Request, HTTPException, Body, UploadFile, File, Form
from fastapi.responses import JSONResponse, Response, FileResponse, HTMLResponse
from pydantic import BaseModel, Field

try:
    import markdown
except ImportError:
    markdown = None

from scripts.routers.sdlc_common import (
    get_db, DB_PATH, INBOX_PATH, log_audit_chain_event,
    map_ticket_type, reverse_map_ticket_type, map_state, reverse_map_state,
    map_priority, reverse_map_priority, is_ui_ticket, has_verified_visual_twin,
    resolve_attachment_path
)

logger = logging.getLogger("sdlc_core")

router = APIRouter(tags=["SDLC Core"])

@router.get("/api/beacon")
def get_live_beacon():
    """
    Returns real-time 4-byte positional telemetry frame for Clio Metal.
    Evaluates queue state and service health in < 2ms.
    """
    import glob
    import os
    from datetime import datetime, timezone

    processing_dir = "/home/james/stacklabs/queue/processing"
    incoming_dir = "/home/james/stacklabs/queue/incoming"

    proc_files = [os.path.basename(f) for f in glob.glob(f"{processing_dir}/WO*.md")]
    inc_files = [os.path.basename(f) for f in glob.glob(f"{incoming_dir}/WO*.md")]

    if proc_files:
        active_wo = proc_files[0]
        # Shorten WO slug for display
        slug = active_wo.replace(".md", "")
        return {
            "frame": "🔨🟡⚡🚀",
            "acronym": "[BLD][RUN][ACT][DSP]",
            "tail": ":: clio",
            "status": "FORGING",
            "active_ticket": slug,
            "hopper_count": len(proc_files) + len(inc_files),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    elif inc_files:
        return {
            "frame": "💾🟡🎯⏳",
            "acronym": "[QUE][NOM][LCK][WAT]",
            "tail": ":: clio",
            "status": "STAGED",
            "active_ticket": None,
            "hopper_count": len(inc_files),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    else:
        return {
            "frame": "⚡🟢🎯🚀",
            "acronym": "[ENG][NOM][LCK][DSP]",
            "tail": ":: clio",
            "status": "NOMINAL",
            "active_ticket": None,
            "hopper_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Parity Endpoints
@router.get("/api/stories")
def get_stories():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT sys_id, number, short_description, state, priority, assigned_to, cmdb_ci 
            FROM sovereign_tickets 
            WHERE type IN ('STRY', 'STORY') 
            ORDER BY sys_updated_on DESC 
            LIMIT 100
        """).fetchall()
        return {"stories": [dict(r) for r in rows]}
    finally:
        conn.close()

@router.get("/api/backlog")
def get_backlog():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT sys_id, number, short_description, state, priority, type, assigned_to 
            FROM sovereign_tickets 
            WHERE state IN (1, 2) 
            ORDER BY sys_updated_on DESC 
            LIMIT 100
        """).fetchall()
        return {"backlog": [dict(r) for r in rows]}
    finally:
        conn.close()

@router.get("/api/sprints/active")
def get_active_sprint_alias():
    return get_forge_active_sprint()

class BoggsLevelRequest(BaseModel):
    level: int


class ApprovalActionRequest(BaseModel):
    action: str
    auth_level: Optional[str] = "omega=1"


class ApprovalUpdateRequest(BaseModel):
    state: Optional[str] = None
    auth_level: Optional[str] = None
    plan_markdown: Optional[str] = None


class ApprovalCreateRequest(BaseModel):
    sys_id: Optional[str] = None
    task_id: str
    assigned_to: Optional[str] = "james"
    title: str
    plan_markdown: Optional[str] = ""
    state: Optional[str] = "Requested"
    auth_level: Optional[str] = "omega=0"


class RemediationRecordPayload(BaseModel):
    tool_name: str
    failed_payload: str
    error_snippet: str
    successful_payload: Optional[str] = None
    remediation_hint: Optional[str] = None
    subsystem: Optional[str] = "general"


def resolve_markdown_images(md_text: str, attachments: list) -> str:
    name_map = {}
    for att in attachments:
        base_name = os.path.basename(att['file_name'])
        name_map[base_name] = att['file_path']
        name_map[att['file_name']] = att['file_path']
        name_map[att['file_name'].lower()] = att['file_path']
        name_map[base_name.lower()] = att['file_path']

    def replace_img(match):
        alt = match.group(1)
        url = match.group(2)
        base_url = os.path.basename(url)
        for key in [base_url, base_url.lower(), url, url.lower()]:
            if key in name_map:
                return f"![{alt}]({name_map[key]})"
        return match.group(0)

    def replace_html_img(match):
        prefix = match.group(1)
        url = match.group(2)
        suffix = match.group(3)
        base_url = os.path.basename(url)
        for key in [base_url, base_url.lower(), url, url.lower()]:
            if key in name_map:
                return f'{prefix}src="{name_map[key]}"{suffix}'
        return match.group(0)

    md_text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_img, md_text)
    md_text = re.sub(r'(<img\s+[^>]*\b)src=["\']([^"\']+)["\']([^>]*>)', replace_html_img, md_text)
    return md_text


def resolve_markdown_links(md_text: str) -> str:
    def replace_link(match):
        label = match.group(1)
        url = match.group(2)
        if url.startswith("file:///"):
            path = url.replace("file://", "")
            return f"[{label}](http://clio.taila01894.ts.net:8095/api/workspace_file?path={path})"
        return match.group(0)
    
    md_text = re.sub(r'\[([^\]]*)\]\((file:///[^)]+)\)', replace_link, md_text)
    return md_text


@router.get("/api/workspace_file")
def serve_workspace_file(path: str):
    path = os.path.abspath(path)
    allowed_roots = [
        "/home/james/stacklabs",
        "/home/james/sovereign_inbox",
        "/home/james/.gemini/antigravity"
    ]
    is_allowed = False
    for root in allowed_roots:
        if path.startswith(root):
            is_allowed = True
            break
            
    if is_allowed and os.path.exists(path) and os.path.isfile(path):
        return FileResponse(path)
    return JSONResponse({"detail": "Not Found or Access Denied"}, status_code=404)


@router.get("/api/tickets/assignees")
def list_assignees():
    try:
        conn = get_db()
        rows = conn.execute("SELECT user_name FROM persona ORDER BY user_name").fetchall()
        conn.close()
        personas = [r["user_name"] for r in rows]
    except Exception as e:
        print("Error querying personas table:", e)
        personas = []
        
    core = ["james", "antigravity", "Gwen", "Cosmos"]
    houses = ["ADVISORY_ENTITY", "HOUSE_OF_GLASS", "HOUSE_OF_LAW", "HOUSE_OF_METAL", "MANDO_WATCHDOG"]
    
    # Merge and sort
    merged = sorted(list(set(core + houses + personas)))
    return merged


@router.get("/api/progress/reports")
def list_progress_reports():
    reports = []
    progress_dirs = [
        "/home/james/sovereign_inbox/today",
        "/home/james/stacklabs/dna/archives/progress"
    ]
    seen_files = set()
    for d in progress_dirs:
        resolved_d = os.path.realpath(d)
        if not os.path.exists(resolved_d):
            continue
        for f in os.listdir(resolved_d):
            if f.startswith("PROGRESS_REPORT_") and f.endswith(".md") and f not in seen_files:
                seen_files.add(f)
                fp = os.path.join(resolved_d, f)
                try:
                    stat = os.stat(fp)
                    with open(fp, "r") as rfile:
                        content = rfile.read(500)
                    reports.append({
                        "filename": f,
                        "path": fp,
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                        "preview": content
                    })
                except Exception:
                    pass
    reports.sort(key=lambda x: x["mtime"], reverse=True)
    return {"status": "SUCCESS", "reports": reports}


@router.post("/api/progress/generate")
def create_progress_report(payload: Optional[dict] = None):
    from scripts.core import progress_reporter
    payload = payload or {}
    report_file = progress_reporter.generate_progress_report(
        session_title=payload.get("session_title", "Active Sovereign Sprint"),
        in_flight=payload.get("in_flight", ""),
        decisions_needed=payload.get("decisions_needed", "None currently. Sprint is on track."),
        trigger_sync=payload.get("trigger_sync", False)
    )
    return {"status": "SUCCESS", "report_file": report_file}


@router.get("/api/tickets")
def list_tickets(
    status: str = None, 
    priority: str = None, 
    epic_id: int = None, 
    feature_id: int = None,
    include_closed: bool = True,
    include_ideas: bool = False,
    queue: Optional[str] = None,
    ticket_type: Optional[str] = None,
    limit_closed: Optional[int] = None,
    limit_resolved: Optional[int] = None
):
    conn = get_db()
    where_clauses = []
    params = []
    
    if not include_closed:
        where_clauses.append("t.state != 5")
        
    if epic_id is not None:
        where_clauses.append("t.epic_id = ?")
        params.append(epic_id)
        
    if feature_id is not None:
        where_clauses.append("t.feature_id = ?")
        params.append(feature_id)
        
    if queue:
        where_clauses.append("t.queue = ?")
        params.append(queue)
    elif not include_ideas and ticket_type != "IDEA":
        # Default operational Kanban filter: exclude speculative Idea Incubator items
        where_clauses.append("(t.type != 'IDEA' AND (t.queue IS NULL OR t.queue != 'incubator'))")
        
    if ticket_type:
        where_clauses.append("t.type = ?")
        params.append(ticket_type)
        
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    query = f"""
        SELECT t.sys_id, t.number as id, t.type, t.parent_sys_id, t.short_description as title, 
               t.description, t.work_notes, t.state as state_int, t.priority as p_int, 
               t.assigned_to, t.cmdb_ci as affected_ci, t.sys_created_on as created_at, 
               t.sys_updated_on as updated_at,
               t.epic_id, t.feature_id,
               e.epic_key, e.epic_name, e.color as epic_color,
               f.title as feature_title,
               q.state as approval_status, q.auth_level as approval_auth_level
        FROM sovereign_tickets t
        LEFT JOIN sovereign_epics e ON e.epic_id = t.epic_id
        LEFT JOIN sdlc_features f ON f.feature_id = t.feature_id
        LEFT JOIN sys_approval_queue q ON q.task_id = t.number OR q.task_id = t.sys_id
        {where_sql}
        ORDER BY t.sys_created_on DESC
    """
    rows = conn.execute(query, params).fetchall()
    
    results = []
    closed_count = 0
    resolved_count = 0
    
    for r in rows:
        d = dict(r)
        d['status'] = map_state(d['state_int'])
        d['priority'] = map_priority(d['p_int'])
        d['ticket_type'] = map_ticket_type(d['type'])
        if not d.get('approval_status'):
            d['approval_status'] = 'NONE'
        
        # Filter if requested
        if status and status != 'ALL' and d['status'] != status:
            continue
        if priority and priority != 'ALL' and d['priority'] != priority:
            continue
            
        if d['status'] == 'CLOSED' and limit_closed is not None:
            if closed_count >= limit_closed:
                continue
            closed_count += 1
            
        if d['status'] == 'DONE' and limit_resolved is not None:
            if resolved_count >= limit_resolved:
                continue
            resolved_count += 1
            
        results.append(d)
        
    conn.close()
    return results


@router.get("/api/ideas")
def list_ideas(
    priority: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Fetch all speculative R&D concepts and mashups staged in the Idea Incubator queue.
    """
    conn = get_db()
    query = """
        SELECT t.sys_id, t.number as id, t.type, t.parent_sys_id, t.short_description as title, 
               t.description, t.work_notes, t.state as state_int, t.priority as p_int, 
               t.assigned_to, t.cmdb_ci as affected_ci, t.sys_created_on as created_at, 
               t.sys_updated_on as updated_at, t.queue
        FROM sovereign_tickets t
        WHERE (t.type = 'IDEA' OR t.queue = 'incubator')
        ORDER BY t.priority ASC, t.sys_created_on DESC
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    
    results = []
    for r in rows:
        d = dict(r)
        d['status'] = map_state(d['state_int'])
        d['priority'] = map_priority(d['p_int'])
        d['ticket_type'] = "IDEA"
        if status and status != 'ALL' and d['status'] != status:
            continue
        if priority and priority != 'ALL' and d['priority'] != priority:
            continue
        results.append(d)
    return results


@router.get("/api/tickets/counts")
def get_ticket_counts():
    conn = get_db()
    rows = conn.execute("SELECT state, COUNT(*) FROM sovereign_tickets GROUP BY state").fetchall()
    conn.close()
    counts = {"OPEN": 0, "IN_PROGRESS": 0, "RESOLVED": 0, "CLOSED": 0, "PLANNING": 0, "TOTAL": 0}
    for r in rows:
        s = map_state(r[0])
        cnt = r[1]
        counts["TOTAL"] += cnt
        if s == "OPEN": counts["OPEN"] += cnt
        elif s == "IN_PROGRESS": counts["IN_PROGRESS"] += cnt
        elif s == "DONE": counts["RESOLVED"] += cnt
        elif s == "CLOSED": counts["CLOSED"] += cnt
        elif s == "PLANNING": counts["PLANNING"] += cnt
    return counts


@router.post("/api/sdlc/autoclose")
def trigger_autoclose(force_all: bool = True):
    try:
        from scripts.autoclose_tickets_daemon import run_autoclose_sweep
        closed = run_autoclose_sweep(DB_PATH, force_all=force_all)
        return {"status": "success", "closed_tickets": closed}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/api/tickets/next_number")
def get_next_ticket_number(category: str = "WO", slug: str = None, increment: bool = False):
    """
    Get the next sequential auto-number and optional hybrid ID for a ticket category.
    If increment=True, increments sys_number.current_number in sovereign_now.db.
    """
    cat = category.upper().strip()
    if cat not in ("WO", "STRY", "DFCT", "ENHC", "INC", "PRB", "CHG", "REQ", "IDEA"):
        cat = "WO"
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT current_number, digits, prefix FROM sys_number WHERE category = ?", (cat,))
    num_row = cursor.fetchone()
    
    if num_row:
        curr_val = num_row['current_number']
        row = conn.execute(f"SELECT number FROM sovereign_tickets WHERE number LIKE '{cat}%' AND number NOT LIKE '{cat}9%' AND number NOT LIKE '{cat}01%' ORDER BY number DESC LIMIT 1").fetchone()
        if row and row['number']:
            try:
                num_part = re.sub(r'[^0-9]', '', str(row['number']).split('-')[0])
                if num_part:
                    val = int(num_part)
                    if 10000 <= val < 90000 and val > curr_val:
                        curr_val = val
            except:
                pass
        next_val = curr_val + 1
        digits = num_row['digits'] or 7
        prefix = num_row['prefix'] or cat
        auto_number = f"{prefix}{str(next_val).zfill(digits)}"
        if increment:
            cursor.execute("UPDATE sys_number SET current_number = ?, sys_updated_on = datetime('now') WHERE category = ?", (next_val, cat))
            conn.commit()
    else:
        row = conn.execute(f"SELECT number FROM sovereign_tickets WHERE number LIKE '{cat}%' AND number NOT LIKE '{cat}9%' AND number NOT LIKE '{cat}01%' ORDER BY number DESC LIMIT 1").fetchone()
        if row:
            try:
                num_part = re.sub(r'[^0-9]', '', row['number'])
                curr_val = int(num_part) if num_part and 10000 <= int(num_part) < 90000 else 10000
            except:
                curr_val = 10000
        else:
            curr_val = 10000
        next_val = curr_val + 1
        auto_number = f"{cat}{str(next_val).zfill(7)}"
        
    conn.close()
    
    hybrid_id = auto_number
    if slug:
        clean_slug = re.sub(r'[^A-Z0-9]+', '-', slug.upper()).strip('-')[:50]
        if clean_slug:
            hybrid_id = f"{auto_number}-{clean_slug}"
            
    return {
        "status": "success",
        "category": cat,
        "current_number": curr_val,
        "next_number": auto_number,
        "hybrid_id": hybrid_id,
        "incremented": increment
    }


@router.get("/api/agents/list")
def list_ai_agents():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT c.sys_id, c.name, c.sys_class_name, c.short_description, c.operational_status, c.assigned_to,
               g.gem_key, g.title as prompt_title, g.sys_updated_on as prompt_updated_on
        FROM cmdb_ci c
        LEFT JOIN sys_gemini_instructions g ON LOWER(g.gem_key) LIKE '%' || LOWER(c.name) || '%'
        WHERE c.sys_class_name = 'cmdb_ci_ai_agent'
        ORDER BY c.name ASC
    """)
    rows = c.fetchall()
    
    # Get relationships
    c.execute("SELECT parent, child, type FROM cmdb_rel_ci")
    rels = c.fetchall()
    conn.close()
    
    agents = []
    for r in rows:
        d = dict(r)
        d["relationships"] = [dict(rel) for rel in rels if rel["parent"] == d["name"] or rel["child"] == d["name"]]
        agents.append(d)
        
    return {"status": "success", "count": len(agents), "agents": agents}


@router.get("/api/agents/instructions")
def list_agent_instructions():
    conn = get_db()
    rows = conn.execute("SELECT sys_id, gem_key, title, description, length(instructions) as prompt_length, sys_updated_on FROM sys_gemini_instructions ORDER BY gem_key ASC").fetchall()
    conn.close()
    return {"status": "success", "count": len(rows), "instructions": [dict(r) for r in rows]}


@router.post("/api/tickets")
async def create_ticket(request: Request):
    data = await request.json()
    conn = None
    try:
        conn = get_db()
        
        ui_type = data.get('ticket_type', 'Story')
        db_type = reverse_map_ticket_type(ui_type)
        
        if data.get('number'):
            new_id = data.get('number')
        elif data.get('id'):
            new_id = data.get('id')
        else:
            # Auto-increment or gen ID based on prefix
            row = conn.execute(f"SELECT number FROM sovereign_tickets WHERE number LIKE '{db_type}%' AND number NOT LIKE '{db_type}9%' AND number NOT LIKE '{db_type}01%' ORDER BY number DESC LIMIT 1").fetchone()
            if row:
                try:
                    last_num = int(re.sub(r'[^0-9]', '', row['number'].split('-')[0]))
                    if 10000 <= last_num < 90000:
                        new_id = f"{db_type}{last_num + 1:07d}"
                    else:
                        new_id = f"{db_type}0010496"
                except:
                    new_id = f"{db_type}{int(datetime.now().timestamp())}"
            else:
                new_id = f"{db_type}0000001"
            
        sys_id = uuid.uuid4().hex
        
        conn.execute("""
            INSERT OR IGNORE INTO sovereign_tickets (
                sys_id, number, type, parent_sys_id, short_description, 
                description, work_notes, state, priority, assigned_to, 
                cmdb_ci, sys_created_on, sys_updated_on
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sys_id,
            new_id,
            db_type,
            data.get('parent_sys_id'),
            data.get('title', ''),
            data.get('description', ''),
            data.get('work_notes', ''),
            reverse_map_state(data.get('status', 'PLANNING')),
            reverse_map_priority(data.get('priority', 'P3')),
            data.get('assigned_to', ''),
            data.get('affected_ci', ''),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        # Check if JIT approval queue staging is requested or ticket is Work Order
        should_stage_approval = data.get('request_approval') is True or data.get('request_approval') == 'true' or db_type == 'WO'
        if should_stage_approval:
            appr_sys_id = f"appr_{new_id.lower().replace('-', '_')}"
            appr_title = data.get('title') or f"Work Order {new_id}"
            appr_plan = data.get('description') or f"Ticket {new_id} staged for JIT Gate Approval"
            
            conn.execute("""
                INSERT OR REPLACE INTO sys_approval_queue (
                    sys_id, task_id, assigned_to, title, plan_markdown, 
                    state, auth_level, sys_created_on, sys_updated_on
                )
                VALUES (?, ?, 'james', ?, ?, 'Requested', 'omega=0', ?, ?)
            """, (
                appr_sys_id,
                new_id,
                appr_title,
                appr_plan,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        conn.commit()
    finally:
        if conn:
            conn.close()

    log_audit_chain_event("ticket.create", {
        "number": new_id,
        "title": data.get("title", ""),
        "ticket_type": ui_type,
        "priority": data.get("priority", "P3"),
        "status": data.get("status", "PLANNING"),
        "assigned_to": data.get("assigned_to", ""),
        "affected_ci": data.get("affected_ci", "")
    })

    return {"id": new_id, "status": "created"}


@router.get("/api/tickets/create")
def create_ticket_get(
    ticket_type: str = "Story",
    title: str = "",
    description: str = "",
    work_notes: str = "",
    status: str = "PLANNING",
    priority: str = "P3",
    assigned_to: str = "",
    affected_ci: str = "",
    parent_sys_id: str = None
):
    conn = None
    try:
        conn = get_db()
        db_type = reverse_map_ticket_type(ticket_type)
        
        # Auto-increment or gen ID based on prefix
        row = conn.execute(f"SELECT number FROM sovereign_tickets WHERE number LIKE '{db_type}%' ORDER BY number DESC LIMIT 1").fetchone()
        if row:
            try:
                last_num = int(row['number'].replace(db_type, ''))
                new_id = f"{db_type}{last_num + 1:07d}"
            except:
                new_id = f"{db_type}{int(datetime.now().timestamp())}"
        else:
            new_id = f"{db_type}0000001"
            
        sys_id = uuid.uuid4().hex
        
        conn.execute("""
            INSERT OR IGNORE INTO sovereign_tickets (
                sys_id, number, type, parent_sys_id, short_description, 
                description, work_notes, state, priority, assigned_to, 
                cmdb_ci, sys_created_on, sys_updated_on
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sys_id,
            new_id,
            db_type,
            parent_sys_id,
            title,
            description,
            work_notes,
            reverse_map_state(status),
            reverse_map_priority(priority),
            assigned_to,
            affected_ci,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        conn.commit()
    finally:
        if conn:
            conn.close()

    log_audit_chain_event("ticket.create", {
        "number": new_id,
        "title": title,
        "ticket_type": ticket_type,
        "priority": priority,
        "status": status,
        "assigned_to": assigned_to,
        "affected_ci": affected_ci
    })

    return {"id": new_id, "status": "created"}


@router.post("/api/tickets/batch_update")
async def batch_update_tickets(request: Request):
    data = await request.json()
    ticket_ids = data.get("ticket_ids", [])
    action = data.get("action", "").upper()
    notes = data.get("work_notes", "")
    
    if not ticket_ids or not action:
        return JSONResponse({"error": "Missing ticket_ids or action"}, status_code=400)
        
    conn = None
    try:
        conn = get_db()
        updated_on = datetime.now().isoformat()
        placeholders = ', '.join(['?'] * len(ticket_ids))
        if action in ("CLOSE", "RESOLVE"):
            blocked_tickets = []
            for tid in ticket_ids:
                row = conn.execute("SELECT sys_id, number, cmdb_ci, short_description, description, work_notes FROM sovereign_tickets WHERE number = ? OR sys_id = ?", (tid, tid)).fetchone()
                if row and is_ui_ticket(dict(row)):
                    row_eval = dict(row)
                    if notes:
                        row_eval['work_notes'] = f"{row_eval.get('work_notes') or ''}\n{notes}"
                    twin_ok, twin_detail = has_verified_visual_twin(conn, row['sys_id'], row['number'], ticket_data=row_eval, return_detail=True)
                    if not twin_ok:
                        blocked_tickets.append(f"{row['number']} ({twin_detail})")
            if blocked_tickets:
                return JSONResponse(
                    status_code=422,
                    content={
                        "error": "SDLC_GOVERNANCE_GATE_VIOLATION",
                        "code": "RULE_IV_2_B",
                        "blocked_tickets": blocked_tickets,
                        "detail": (
                            f"⛔ HARD-GATE [Rule IV.2.b Violation]: Cannot batch {action} UI ticket(s) due to visual twin gate:\n" +
                            "\n".join(blocked_tickets)
                        )
                    }
                )
                
        if action == "CLOSE":
            if notes:
                query = f"""
                    UPDATE sovereign_tickets 
                    SET state = 5, 
                        work_notes = coalesce(work_notes, '') || '\n[Agent Journal - ' || ? || ' - bulk] ' || ?,
                        sys_updated_on = ? 
                    WHERE number IN ({placeholders}) OR sys_id IN ({placeholders})
                """
                params = [updated_on, notes, updated_on] + ticket_ids + ticket_ids
            else:
                query = f"""
                    UPDATE sovereign_tickets 
                    SET state = 5, sys_updated_on = ? 
                    WHERE number IN ({placeholders}) OR sys_id IN ({placeholders})
                """
                params = [updated_on] + ticket_ids + ticket_ids
            conn.execute(query, params)
            conn.commit()
            return {"status": "success", "message": f"Successfully closed {len(ticket_ids)} tickets."}
            
        elif action == "RESOLVE":
            if notes:
                query = f"""
                    UPDATE sovereign_tickets 
                    SET state = 4, 
                        work_notes = coalesce(work_notes, '') || '\n[Agent Journal - ' || ? || ' - bulk] ' || ?,
                        sys_updated_on = ? 
                    WHERE number IN ({placeholders}) OR sys_id IN ({placeholders})
                """
                params = [updated_on, notes, updated_on] + ticket_ids + ticket_ids
            else:
                query = f"""
                    UPDATE sovereign_tickets 
                    SET state = 4, sys_updated_on = ? 
                    WHERE number IN ({placeholders}) OR sys_id IN ({placeholders})
                """
                params = [updated_on] + ticket_ids + ticket_ids
            conn.execute(query, params)
            conn.commit()
            return {"status": "success", "message": f"Successfully resolved {len(ticket_ids)} tickets."}

        elif action == "REOPEN":
            query = f"""
                UPDATE sovereign_tickets 
                SET state = 1, sys_updated_on = ? 
                WHERE number IN ({placeholders}) OR sys_id IN ({placeholders})
            """
            params = [updated_on] + ticket_ids + ticket_ids
            conn.execute(query, params)
            conn.commit()
            return {"status": "success", "message": f"Successfully reopened {len(ticket_ids)} tickets."}

        elif action == "ASSIGN":
            assignee = data.get("assigned_to", "UNASSIGNED")
            query = f"""
                UPDATE sovereign_tickets 
                SET assigned_to = ?, sys_updated_on = ? 
                WHERE number IN ({placeholders}) OR sys_id IN ({placeholders})
            """
            params = [assignee, updated_on] + ticket_ids + ticket_ids
            conn.execute(query, params)
            conn.commit()
            return {"status": "success", "message": f"Successfully assigned {len(ticket_ids)} tickets to {assignee}."}

        elif action == "SET_PRIORITY":
            priority = data.get("priority", "P3")
            query = f"""
                UPDATE sovereign_tickets 
                SET priority = ?, sys_updated_on = ? 
                WHERE number IN ({placeholders}) OR sys_id IN ({placeholders})
            """
            params = [priority, updated_on] + ticket_ids + ticket_ids
            conn.execute(query, params)
            conn.commit()
            return {"status": "success", "message": f"Successfully updated priority to {priority} for {len(ticket_ids)} tickets."}

    finally:
        if conn:
            conn.close()
            
    return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)


@router.post("/api/audit/append")
@router.post("/api/audit/log")
async def api_audit_append(request: Request):
    """Append a tamper-evident cryptographic event to the Merkle audit chain."""
    if SovereignAuditChain is None:
        raise HTTPException(status_code=500, detail="SovereignAuditChain module unavailable")
    data = await request.json()
    event_type = data.get("event_type")
    payload = data.get("payload")
    signature_key = data.get("signature_key")
    if not event_type or payload is None:
        raise HTTPException(status_code=400, detail="Missing event_type or payload")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be a JSON object")
    try:
        chain = SovereignAuditChain(db_path=DB_PATH)
        res = chain.append(event_type, payload, signature_key=signature_key)
        return {"status": "appended", "seq": res["seq"], "hash": res["hash"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/audit/verify")
def api_audit_verify(from_seq: int = 1, to_seq: Optional[int] = None):
    """Verify cryptographic hash and linkage integrity across the audit chain."""
    if SovereignAuditChain is None:
        raise HTTPException(status_code=500, detail="SovereignAuditChain module unavailable")
    try:
        chain = SovereignAuditChain(db_path=DB_PATH)
        return chain.verify(from_seq=from_seq, to_seq=to_seq)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/audit/latest")
def api_audit_latest():
    """Retrieve the latest hash, sequence, and total count of the audit chain."""
    if SovereignAuditChain is None:
        raise HTTPException(status_code=500, detail="SovereignAuditChain module unavailable")
    try:
        chain = SovereignAuditChain(db_path=DB_PATH)
        latest = chain.latest()
        return {
            "latest": latest,
            "seq": latest["seq"] if latest else 0,
            "hash": latest["hash"] if latest else None,
            "count": chain.count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/audit/entries")
def api_audit_entries(from_seq: int = 1, to_seq: Optional[int] = None, limit: int = 50):
    """List audit chain entries in ascending sequence order."""
    if SovereignAuditChain is None:
        raise HTTPException(status_code=500, detail="SovereignAuditChain module unavailable")
    try:
        chain = SovereignAuditChain(db_path=DB_PATH)
        return chain.get_entries(from_seq=from_seq, to_seq=to_seq, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/sdlc/initiatives")
def list_initiatives():
    conn = get_db()
    rows = conn.execute("""
        SELECT i.*, 
               COUNT(e.epic_id) as total_epics,
               SUM(CASE WHEN e.status = 'RESOLVED' THEN 1 ELSE 0 END) as completed_epics
        FROM sdlc_initiatives i
        LEFT JOIN sovereign_epics e ON e.initiative_id = i.initiative_id
        GROUP BY i.initiative_id
        ORDER BY i.created_at ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/api/sdlc/initiatives")
async def create_initiative(request: Request):
    data = await request.json()
    init_id = data.get("initiative_id")
    conn = get_db()
    if not init_id:
        row = conn.execute("SELECT initiative_id FROM sdlc_initiatives ORDER BY initiative_id DESC LIMIT 1").fetchone()
        if row and row['initiative_id'].startswith('INIT-'):
            try:
                num = int(row['initiative_id'].replace('INIT-', '')) + 1
                init_id = f"INIT-{num:03d}"
            except:
                init_id = f"INIT-{int(datetime.now().timestamp())}"
        else:
            init_id = "INIT-001"
            
    conn.execute("""
        INSERT INTO sdlc_initiatives (initiative_id, name, code, description, owner, status, icon, color)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        init_id,
        data.get("name", "Untitled Initiative"),
        data.get("code", init_id),
        data.get("description", ""),
        data.get("owner", "james"),
        data.get("status", "ACTIVE"),
        data.get("icon", "🚀"),
        data.get("color", "#00b4d8")
    ))
    conn.commit()
    conn.close()
    return {"initiative_id": init_id, "status": "created"}


@router.get("/api/sdlc/epics")
def list_epics(initiative_id: str = None, status: str = None):
    conn = get_db()
    query = "SELECT * FROM v_sdlc_epic_rollup WHERE 1=1"
    params = []
    if initiative_id:
        query += " AND initiative_id = ?"
        params.append(initiative_id)
    if status and status != 'ALL':
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY epic_id ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/api/sdlc/epics")
async def create_epic(request: Request):
    data = await request.json()
    conn = get_db()
    
    # Auto-generate epic_key if missing
    epic_key = data.get("epic_key")
    if not epic_key:
        row = conn.execute("SELECT epic_id FROM sovereign_epics ORDER BY epic_id DESC LIMIT 1").fetchone()
        next_id = (row['epic_id'] + 1) if row else 1
        epic_key = f"EPIC-{next_id:03d}"
        
    cursor = conn.execute("""
        INSERT INTO sovereign_epics (
            initiative_id, epic_key, epic_name, description, owner,
            status, health, color, risk_level, business_value, architecture_spec_url, target_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("initiative_id"),
        epic_key,
        data.get("epic_name", "Untitled Epic"),
        data.get("description", ""),
        data.get("owner", "james"),
        data.get("status", "IN_PROGRESS"),
        data.get("health", "ON_TRACK"),
        data.get("color", "#00b4d8"),
        data.get("risk_level", "LOW"),
        data.get("business_value", ""),
        data.get("architecture_spec_url", ""),
        data.get("target_date")
    ))
    new_epic_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"epic_id": new_epic_id, "epic_key": epic_key, "status": "created"}


@router.get("/api/sdlc/features")
def list_features(epic_id: int = None):
    conn = get_db()
    query = """
        SELECT f.*, e.epic_key, e.epic_name, e.color as epic_color,
               COUNT(t.number) as total_tickets,
               SUM(CASE WHEN t.state IN (4, 5) THEN 1 ELSE 0 END) as completed_tickets
        FROM sdlc_features f
        LEFT JOIN sovereign_epics e ON e.epic_id = f.epic_id
        LEFT JOIN sovereign_tickets t ON t.feature_id = f.feature_id
        WHERE 1=1
    """
    params = []
    if epic_id is not None:
        query += " AND f.epic_id = ?"
        params.append(epic_id)
    query += " GROUP BY f.feature_id ORDER BY f.feature_id ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/api/sdlc/features")
async def create_feature(request: Request):
    data = await request.json()
    conn = get_db()
    epic_id = data.get("epic_id")
    if not epic_id:
        conn.close()
        return JSONResponse({"error": "epic_id is required"}, status_code=400)
        
    feature_key = data.get("feature_key")
    if not feature_key:
        row = conn.execute("SELECT feature_id FROM sdlc_features WHERE epic_id = ? ORDER BY feature_id DESC LIMIT 1", (epic_id,)).fetchone()
        next_num = 1
        if row:
            next_num = row['feature_id'] + 1
        feature_key = f"FEAT-{epic_id:03d}-{next_num}"
        
    cursor = conn.execute("""
        INSERT INTO sdlc_features (epic_id, feature_key, title, description, status, priority, owner, acceptance_criteria)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        epic_id,
        feature_key,
        data.get("title", "Untitled Feature"),
        data.get("description", ""),
        data.get("status", "OPEN"),
        data.get("priority", "P3"),
        data.get("owner", "james"),
        data.get("acceptance_criteria", "")
    ))
    new_feat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"feature_id": new_feat_id, "feature_key": feature_key, "status": "created"}


@router.get("/api/sdlc/hierarchy")
def get_hierarchy_tree():
    conn = get_db()
    
    # 1. Fetch initiatives
    init_rows = conn.execute("SELECT * FROM sdlc_initiatives ORDER BY created_at ASC").fetchall()
    initiatives = [dict(r) for r in init_rows]
    
    # 2. Fetch epics rollup
    epic_rows = conn.execute("SELECT * FROM v_sdlc_epic_rollup ORDER BY epic_id ASC").fetchall()
    epics = [dict(r) for r in epic_rows]
    
    # 3. Fetch features
    feat_rows = conn.execute("""
        SELECT f.*, 
               COUNT(t.number) as total_tickets,
               SUM(CASE WHEN t.state IN (4, 5) THEN 1 ELSE 0 END) as completed_tickets
        FROM sdlc_features f
        LEFT JOIN sovereign_tickets t ON t.feature_id = f.feature_id
        GROUP BY f.feature_id
        ORDER BY f.feature_id ASC
    """).fetchall()
    features = [dict(r) for r in feat_rows]
    
    # 4. Fetch linked tickets
    ticket_rows = conn.execute("""
        SELECT t.sys_id, t.number as id, t.type, t.short_description as title, 
               t.description, t.state as state_int, t.priority as p_int, 
               t.assigned_to, t.cmdb_ci as affected_ci, t.epic_id, t.feature_id,
               t.sys_created_on as created_at
        FROM sovereign_tickets t
        WHERE t.epic_id IS NOT NULL
        ORDER BY t.sys_created_on DESC
    """).fetchall()
    
    tickets_by_epic = {}
    tickets_by_feat = {}
    for r in ticket_rows:
        td = dict(r)
        td['status'] = map_state(td['state_int'])
        td['priority'] = map_priority(td['p_int'])
        td['ticket_type'] = map_ticket_type(td['type'])
        
        eid = td['epic_id']
        fid = td['feature_id']
        
        if eid not in tickets_by_epic:
            tickets_by_epic[eid] = []
        tickets_by_epic[eid].append(td)
        
        if fid:
            if fid not in tickets_by_feat:
                tickets_by_feat[fid] = []
            tickets_by_feat[fid].append(td)
            
    # Assemble nested tree
    features_by_epic = {}
    for f in features:
        eid = f['epic_id']
        if eid not in features_by_epic:
            features_by_epic[eid] = []
        f['tickets'] = tickets_by_feat.get(f['feature_id'], [])
        features_by_epic[eid].append(f)
        
    epics_by_init = {}
    for e in epics:
        init_id = e['initiative_id'] or 'UNASSIGNED'
        if init_id not in epics_by_init:
            epics_by_init[init_id] = []
        e['features'] = features_by_epic.get(e['epic_id'], [])
        e['tickets'] = tickets_by_epic.get(e['epic_id'], [])
        epics_by_init[init_id].append(e)
        
    for i in initiatives:
        i['epics'] = epics_by_init.get(i['initiative_id'], [])
        
    # Unassigned epics container
    unassigned_epics = epics_by_init.get('UNASSIGNED', [])
    if unassigned_epics:
        initiatives.append({
            "initiative_id": "INIT-STANDALONE",
            "name": "Standalone & Cross-Stack Epics",
            "code": "STANDALONE",
            "description": "Epics not bound to a primary top-level initiative.",
            "owner": "james",
            "status": "ACTIVE",
            "icon": "📦",
            "color": "#64748b",
            "epics": unassigned_epics
        })
        
    conn.close()
    return {"initiatives": initiatives, "total_epics": len(epics), "total_features": len(features)}


@router.post("/api/tickets/batch_link")
async def batch_link_tickets(request: Request):
    data = await request.json()
    ticket_ids = data.get("ticket_ids", [])
    epic_id = data.get("epic_id")
    feature_id = data.get("feature_id")
    
    if not ticket_ids or epic_id is None:
        return JSONResponse({"error": "ticket_ids and epic_id are required"}, status_code=400)
        
    conn = get_db()
    placeholders = ', '.join(['?'] * len(ticket_ids))
    if feature_id is not None:
        query = f"UPDATE sovereign_tickets SET epic_id = ?, feature_id = ?, sys_updated_on = CURRENT_TIMESTAMP WHERE number IN ({placeholders}) OR sys_id IN ({placeholders})"
        params = [epic_id, feature_id] + ticket_ids + ticket_ids
    else:
        query = f"UPDATE sovereign_tickets SET epic_id = ?, sys_updated_on = CURRENT_TIMESTAMP WHERE number IN ({placeholders}) OR sys_id IN ({placeholders})"
        params = [epic_id] + ticket_ids + ticket_ids
        
    conn.execute(query, params)
    conn.commit()
    conn.close()
    return {"status": "success", "linked_count": len(ticket_ids)}


@router.get("/api/sdlc/dependencies")
def list_dependencies():
    conn = get_db()
    rows = conn.execute("SELECT * FROM sovereign_ticket_dependencies ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/api/sdlc/dependencies")
async def create_dependency(request: Request):
    data = await request.json()
    conn = get_db()
    conn.execute("""
        INSERT OR IGNORE INTO sovereign_ticket_dependencies (predecessor_id, successor_id, dependency_type)
        VALUES (?, ?, ?)
    """, (
        data.get("predecessor_id"),
        data.get("successor_id"),
        data.get("dependency_type", "BLOCKS")
    ))
    conn.commit()
    conn.close()
    return {"status": "created"}


@router.get("/api/stats")
def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM sovereign_tickets").fetchone()[0]
    
    bystates = conn.execute("SELECT state as state_int, COUNT(*) as cnt FROM sovereign_tickets GROUP BY state").fetchall()
    by_status = {map_state(r['state_int']): r['cnt'] for r in bystates}
    
    bypriority = conn.execute("SELECT priority as p_int, COUNT(*) as cnt FROM sovereign_tickets GROUP BY priority").fetchall()
    by_priority = {map_priority(r['p_int']): r['cnt'] for r in bypriority}
    
    byci = conn.execute("SELECT cmdb_ci as assigned_ci, COUNT(*) as cnt FROM sovereign_tickets WHERE cmdb_ci != '' AND cmdb_ci IS NOT NULL GROUP BY cmdb_ci").fetchall()
    by_ci = {r['assigned_ci']: r['cnt'] for r in byci}
    
    conn.close()
    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_ci": by_ci
    }


@router.get("/api/forge/active_sprint")
def get_forge_active_sprint():
    """
    Returns real-time active sprint status, destination URL, and hopper telemetry
    directly from /home/james/sovereign_inbox/pilot_drops/forge_beacon_state.json
    and live queue files. Zero code re-deploys required.
    """
    import glob
    import os
    import json
    
    state_file = "/home/james/sovereign_inbox/pilot_drops/forge_beacon_state.json"
    incoming_dir = "/home/james/sovereign_inbox/queue/incoming"
    processing_dir = "/home/james/sovereign_inbox/queue/processing"
    
    incoming_files = [os.path.basename(f) for f in glob.glob(f"{incoming_dir}/WO*.md")]
    processing_files = [os.path.basename(f) for f in glob.glob(f"{processing_dir}/WO*.md")]
    hopper_count = len(processing_files + incoming_files)
    
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
            state["hopper_count"] = hopper_count
            return state
        except Exception as e:
            pass
            
    return {
        "enabled": False,
        "status": "READY",
        "hopper_count": hopper_count,
        "headline": "Queue ready for dispatch",
        "link_url": "https://stacklabsllc.com",
        "ports": [8088, 8095],
        "host": "clio"
    }


@router.get("/api/system/properties/boggs_level")
def get_boggs_level():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT value FROM sys_properties WHERE name = 'glide.sovereign.boggs_level'")
        row = c.fetchone()
        level = int(row[0]) if row and str(row[0]).isdigit() else 3
        levels = {1: "Lurker", 2: "Pacer", 3: "Balanced", 4: "Agitator", 5: "Yapper"}
        return {"status": "SUCCESS", "level": level, "mode": levels.get(level, "Balanced"), "property": "glide.sovereign.boggs_level"}
    finally:
        conn.close()


@router.put("/api/system/properties/boggs_level")
def update_boggs_level(req: BoggsLevelRequest):
    conn = get_db()
    c = conn.cursor()
    try:
        level = max(1, min(5, req.level))
        levels = {1: "Lurker", 2: "Pacer", 3: "Balanced", 4: "Agitator", 5: "Yapper"}
        c.execute("""
            INSERT INTO sys_properties (name, value, description, sys_updated_on)
            VALUES ('glide.sovereign.boggs_level', ?, 'Systemic advocate reactivity level (1-5)', CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET value = excluded.value, sys_updated_on = CURRENT_TIMESTAMP
        """, (str(level),))
        conn.commit()
        return {"status": "SUCCESS", "level": level, "mode": levels.get(level, "Balanced")}
    finally:
        conn.close()


@router.get("/api/v1/approvals/pending")
def get_pending_approvals():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT sys_id, task_id, assigned_to, title, plan_markdown, state, auth_level, sys_created_on
            FROM sys_approval_queue
            WHERE state IN ('Requested', 'Pending', 'STAGED')
            ORDER BY sys_created_on DESC
        """)
        rows = [dict(r) for r in c.fetchall()]
        return {"status": "SUCCESS", "approvals": rows, "count": len(rows)}
    finally:
        conn.close()


@router.get("/api/approvals")
def list_approvals(
    state: Optional[str] = None,
    auth_level: Optional[str] = None,
    task_id: Optional[str] = None,
    limit: int = 50
):
    conn = get_db()
    c = conn.cursor()
    try:
        where = []
        params = []
        if state:
            where.append("state = ?")
            params.append(state)
        if auth_level:
            if "%" in auth_level:
                where.append("auth_level LIKE ?")
            else:
                where.append("auth_level = ?")
            params.append(auth_level)
        if task_id:
            where.append("(task_id = ? OR sys_id = ?)")
            params.extend([task_id, task_id])
        
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        query = f"""
            SELECT sys_id, task_id, assigned_to, title, plan_markdown, state, auth_level, sys_created_on, sys_updated_on
            FROM sys_approval_queue
            {where_sql}
            ORDER BY sys_created_on ASC
            LIMIT ?
        """
        params.append(limit)
        c.execute(query, tuple(params))
        rows = [dict(r) for r in c.fetchall()]
        return {"status": "SUCCESS", "approvals": rows, "count": len(rows)}
    finally:
        conn.close()


@router.post("/api/approvals")
def create_approval_record(req: ApprovalCreateRequest):
    conn = get_db()
    c = conn.cursor()
    try:
        sys_id = req.sys_id or f"appr_{uuid.uuid4().hex[:12]}"
        c.execute("""
            INSERT INTO sys_approval_queue (sys_id, task_id, assigned_to, title, plan_markdown, state, auth_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sys_id) DO UPDATE SET
                task_id = excluded.task_id,
                assigned_to = excluded.assigned_to,
                title = excluded.title,
                plan_markdown = excluded.plan_markdown,
                state = excluded.state,
                auth_level = excluded.auth_level,
                sys_updated_on = CURRENT_TIMESTAMP
        """, (sys_id, req.task_id, req.assigned_to, req.title, req.plan_markdown, req.state, req.auth_level))
        conn.commit()
        return {"status": "SUCCESS", "sys_id": sys_id, "task_id": req.task_id}
    finally:
        conn.close()


@router.get("/api/system/pollers/status")
async def get_pollers_status():
    """Retrieve live heartbeat telemetry and systemd process health for Sovereign background pollers."""
    from pathlib import Path
    now = time.time()
    
    # 1. Scratchpad Poller
    scratchpad_hb_file = Path("/home/james/stacklabs/logs/scratch_pad_poller_heartbeat.json")
    scratchpad_info = {
        "service_name": "scratch-pad-poller.service",
        "active": False,
        "pid": None,
        "poll_count": 0,
        "seconds_since_heartbeat": None,
        "status": "STOPPED",
        "scratch_pad_sha256": "",
        "unresolved_tasks_count": 0,
        "last_heartbeat_iso": None
    }
    if scratchpad_hb_file.exists():
        try:
            with open(scratchpad_hb_file, "r") as f:
                data = json.load(f)
                ts = data.get("timestamp", 0)
                sec_ago = max(0.0, round(now - ts, 2))
                scratchpad_info.update({
                    "active": sec_ago < 10.0,
                    "pid": data.get("pid"),
                    "poll_count": data.get("poll_count", 0),
                    "seconds_since_heartbeat": sec_ago,
                    "status": data.get("status", "LISTENING") if sec_ago < 10.0 else "STALE",
                    "scratch_pad_sha256": data.get("scratch_pad_sha256", ""),
                    "unresolved_tasks_count": data.get("unresolved_tasks_count", 0),
                    "last_heartbeat_iso": data.get("iso_time")
                })
        except Exception as e:
            scratchpad_info["error"] = str(e)

    # 2. FanStack Poller
    fanstack_hb_file = Path("/home/james/stacklabs/logs/fanstack_poller_heartbeat.json")
    fanstack_info = {
        "service_name": "fanstack-poller.service",
        "active": False,
        "pid": None,
        "seconds_since_heartbeat": None,
        "status": "STOPPED",
        "active_games_count": 0,
        "last_play_desc": "",
        "last_heartbeat_iso": None
    }
    if fanstack_hb_file.exists():
        try:
            with open(fanstack_hb_file, "r") as f:
                data = json.load(f)
                ts = data.get("timestamp", 0)
                sec_ago = max(0.0, round(now - ts, 2))
                fanstack_info.update({
                    "active": sec_ago < 15.0,
                    "pid": data.get("pid"),
                    "seconds_since_heartbeat": sec_ago,
                    "status": data.get("status", "STREAMING") if sec_ago < 15.0 else "STALE",
                    "active_games_count": data.get("active_games_count", 0),
                    "last_play_desc": data.get("last_play_desc", ""),
                    "last_heartbeat_iso": data.get("iso_time")
                })
        except Exception as e:
            fanstack_info["error"] = str(e)

    import datetime as _dt
    return {
        "status": "success",
        "timestamp": now,
        "iso_time": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "pollers": {
            "scratch_pad_poller": scratchpad_info,
            "fanstack_poller": fanstack_info
        }
    }


@router.post("/api/system/remediation/record")
async def api_record_remediation(payload: RemediationRecordPayload):
    """Record a failure or pair with subsequent successful resolution."""
    try:
        from core.remediation_engine import record_failure, pair_and_commit_success
        if payload.successful_payload:
            record_failure(payload.tool_name, payload.failed_payload, payload.error_snippet, payload.subsystem or "general")
            rec = pair_and_commit_success(payload.tool_name, payload.successful_payload, payload.remediation_hint)
            return {"status": "success", "action": "paired", "remediation": rec}
        else:
            rec = record_failure(payload.tool_name, payload.failed_payload, payload.error_snippet, payload.subsystem or "general")
            return {"status": "success", "action": "failure_recorded", "record": rec}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/system/remediation/check")
async def api_check_remediation(tool_name: str, payload: str):
    """Check if tool call matches a known failure with a verified resolution."""
    try:
        from core.remediation_engine import check_reflex
        res = check_reflex(tool_name, payload)
        if res:
            return {"matched": True, "reflex": res}
        return {"matched": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/system/remediation/top")
async def api_get_top_remediations(limit: int = 10):
    """Retrieve top error remediation reflexes for agent context priming."""
    try:
        from core.remediation_engine import get_top_remediations
        items = get_top_remediations(limit)
        return {"status": "success", "count": len(items), "remediations": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/sir/alerts")
async def get_sir_alerts_endpoint(limit: int = 50, vertical: Optional[str] = None):
    """Retrieve prioritized SIR regulatory & municipal intelligence alerts."""
    try:
        try:
            from scripts.sir_recon_engine import list_sir_alerts
        except ImportError:
            from sir_recon_engine import list_sir_alerts
        alerts = list_sir_alerts(limit=limit, vertical=vertical)
        return {"status": "success", "count": len(alerts), "alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/sir/sweep")
async def trigger_sir_sweep_endpoint(mock: bool = True):
    """Trigger an on-demand regulatory docket sweep."""
    try:
        try:
            from scripts.sir_recon_engine import run_mock_sweep
        except ImportError:
            from sir_recon_engine import run_mock_sweep
        result = run_mock_sweep()
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/sir/status")
async def get_sir_status_endpoint():
    """Get SIR docket and alert inventory counts."""
    try:
        try:
            from core.db import get_db
        except ImportError:
            from scripts.core.db import get_db
        with get_db() as conn:
            docket_count = conn.execute("SELECT COUNT(*) FROM sir_dockets").fetchone()[0]
            alert_count = conn.execute("SELECT COUNT(*) FROM sir_alerts").fetchone()[0]
            critical_alerts = conn.execute("SELECT COUNT(*) FROM sir_alerts WHERE severity = 'CRITICAL'").fetchone()[0]
        return {
            "status": "online",
            "dockets_indexed": docket_count,
            "total_alerts": alert_count,
            "critical_alerts": critical_alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/recon/prospects")
def get_recon_prospects_endpoint():
    """Retrieve all audited prospects from recon_sentinel.db."""
    if not os.path.exists(RECON_DB_PATH):
        return []
    with sqlite3.connect(RECON_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM prospects ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


@router.get("/ingestor", response_class=HTMLResponse)
def serve_ingestor():
    with open("/home/james/stacklabs/scripts/sovereign_ingestor.html", "r") as f:
        return f.read()


@router.get("/", response_class=HTMLResponse)
@router.head("/", response_class=HTMLResponse)
def serve_ui(request: Request):
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host", "")).lower()
    if host.startswith("chat.") or host.startswith("v6."):
        chat_path = Path("/home/james/stacklabs/apps/horizon_scratchpad/chat.html")
        if chat_path.exists():
            return HTMLResponse(chat_path.read_text(encoding="utf-8"))
    with open("/home/james/stacklabs/scripts/sdlc_portal.html", "r") as f:
        return f.read()


@router.get("/attachments/{filename:path}")
def serve_attachment(filename: str):
    p = resolve_attachment_path(filename)
    if p:
        return FileResponse(p)
    return JSONResponse({"detail": "Not Found"}, status_code=404)


@router.get("/home/james/sovereign_inbox/{filename:path}")
def serve_absolute_inbox(filename: str):
    p = os.path.join(INBOX_PATH, filename)
    if os.path.exists(p) and p.startswith(INBOX_PATH):
        return FileResponse(p)
    return JSONResponse({"detail": "Not Found"}, status_code=404)


@router.get("/api/tickets/{ticket_id}/attachments")
def list_attachments(ticket_id: str):
    conn = get_db()
    sys_id = ticket_id
    t_row = conn.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ? OR sys_id = ?", (ticket_id, ticket_id)).fetchone()
    if t_row:
        sys_id = t_row['sys_id']
    rows = conn.execute("""
        SELECT sys_id, file_name, content_type, file_path, sys_created_on 
        FROM sys_attachment 
        WHERE table_name = 'sovereign_tickets' AND (table_sys_id = ? OR table_sys_id = ?)
    """, (sys_id, ticket_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/api/tickets/{ticket_id}/attachments")
async def upload_attachment(ticket_id: str, file: UploadFile = File(...)):
    filename = file.filename
    ext = os.path.splitext(filename)[1]
    sys_id = uuid.uuid4().hex
    new_filename = f"{sys_id}{ext}"
    
    tickets_dir = os.path.join(INBOX_PATH, "tickets")
    if not os.path.exists(tickets_dir):
        try:
            os.makedirs(tickets_dir)
        except:
            pass
            
    filepath = os.path.join(tickets_dir, new_filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    conn = None
    try:
        conn = get_db()
        t_sys_id = ticket_id
        t_row = conn.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ? OR sys_id = ?", (ticket_id, ticket_id)).fetchone()
        if t_row:
            t_sys_id = t_row['sys_id']
            
        conn.execute("""
            INSERT OR IGNORE INTO sys_attachment (sys_id, table_name, table_sys_id, file_name, content_type, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sys_id, 'sovereign_tickets', t_sys_id, filename, file.content_type, f"/attachments/{new_filename}"))
        conn.commit()
    finally:
        if conn:
            conn.close()
    
    # Automate archiving/decluttering of walkthroughs/plans from root inbox to respective subfolders
    local_source = os.path.join(INBOX_PATH, filename)
    if os.path.exists(local_source) and os.path.isfile(local_source):
        filename_lower = filename.lower()
        if "walkthrough" in filename_lower:
            dest_dir = os.path.join(INBOX_PATH, "walkthroughs")
        elif "implementation_plan" in filename_lower or "implementationplan" in filename_lower:
            dest_dir = os.path.join(INBOX_PATH, "implementation_plans")
        elif "report" in filename_lower:
            dest_dir = os.path.join(INBOX_PATH, "reports")
        else:
            dest_dir = tickets_dir
            
        os.makedirs(dest_dir, exist_ok=True)
        local_dest = os.path.join(dest_dir, filename)
        try:
            shutil.move(local_source, local_dest)
        except Exception as e:
            print(f"Error moving file: {e}")
            
    return {"sys_id": sys_id, "file_name": filename, "url": f"/attachments/{new_filename}"}


@router.delete("/api/tickets/{ticket_id}/attachments/{sys_id}")
def delete_attachment(ticket_id: str, sys_id: str):
    conn = None
    try:
        conn = get_db()
        row = conn.execute("SELECT file_path FROM sys_attachment WHERE sys_id = ?", (sys_id,)).fetchone()
        if row:
            file_path = row['file_path']
            filename = file_path.replace('/attachments/', '')
            full_path = resolve_attachment_path(filename)
            if full_path and os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass
        conn.execute("DELETE FROM sys_attachment WHERE sys_id = ?", (sys_id,))
        conn.commit()
    finally:
        if conn:
            conn.close()
    return {"status": "deleted", "id": sys_id}


@router.post("/api/ideas/{idea_id}/promote")
def promote_idea(idea_id: str, target_type: str = "STRY", priority: int = 2):
    """
    Atomically promote an Idea Incubator concept into an active Work Order or Story in the operational sprint backlog.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT sys_id, number, short_description, description, cmdb_ci, work_notes, priority 
        FROM sovereign_tickets 
        WHERE sys_id = ? OR number = ?
    """, (idea_id, idea_id))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Idea '{idea_id}' not found.")
        
    db_sys_id, old_num, title, desc, cmdb_ci, work_notes, curr_pri = (
        row['sys_id'], row['number'], row['short_description'], 
        row['description'], row['cmdb_ci'], row['work_notes'] or "", row['priority']
    )
    
    tgt_type = target_type.upper()
    if tgt_type not in ("STRY", "WO", "ENHC", "DFCT"):
        tgt_type = "STRY"
        
    cursor.execute("SELECT current_number, digits, prefix FROM sys_number WHERE category = ?", (tgt_type,))
    num_row = cursor.fetchone()
    if num_row:
        next_val = num_row['current_number'] + 1
        new_num = f"{num_row['prefix']}{str(next_val).zfill(num_row['digits'])}"
        cursor.execute("UPDATE sys_number SET current_number = ?, sys_updated_on = datetime('now') WHERE category = ?", (next_val, tgt_type))
    else:
        new_num = f"{tgt_type}{uuid.uuid4().hex[:8].upper()}"
        
    slug = re.sub(r'[^A-Z0-9]+', '-', title.upper()).strip('-')[:30]
    promoted_hybrid_id = f"{new_num}-{slug}"
    
    promotion_log = f"\n[PROMOTION {datetime.now().isoformat()}] Promoted from Idea '{old_num}' to operational {tgt_type} backlog as '{promoted_hybrid_id}' by Pilot."
    updated_work_notes = (work_notes + promotion_log).strip()
    
    cursor.execute("""
        UPDATE sovereign_tickets 
        SET number = ?, type = ?, queue = 'operational', state = 1, priority = ?, work_notes = ?, sys_updated_on = datetime('now')
        WHERE sys_id = ?
    """, (promoted_hybrid_id, tgt_type, priority or curr_pri, updated_work_notes, db_sys_id))
    
    conn.commit()
    conn.close()
    
    return {
        "status": "PROMOTED",
        "idea_id": old_num,
        "promoted_ticket_id": promoted_hybrid_id,
        "target_type": tgt_type,
        "queue": "operational",
        "state": "OPEN",
        "title": title
    }


@router.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    conn = get_db()
    row = conn.execute("""
        SELECT t.sys_id, t.number as id, t.type, t.parent_sys_id, t.short_description as title, 
               t.description, t.work_notes, t.state as state_int, t.priority as p_int, 
               t.assigned_to, t.cmdb_ci as affected_ci, t.sys_created_on as created_at, 
               t.sys_updated_on as updated_at,
               t.epic_id, t.feature_id,
               e.epic_key, e.epic_name, e.color as epic_color,
               f.title as feature_title,
               q.state as approval_status, q.auth_level as approval_auth_level
        FROM sovereign_tickets t
        LEFT JOIN sovereign_epics e ON e.epic_id = t.epic_id
        LEFT JOIN sdlc_features f ON f.feature_id = t.feature_id
        LEFT JOIN sys_approval_queue q ON q.task_id = t.number OR q.task_id = t.sys_id
        WHERE t.number = ? OR t.sys_id = ?
    """, (ticket_id, ticket_id)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d['status'] = map_state(d['state_int'])
        d['priority'] = map_priority(d['p_int'])
        d['ticket_type'] = map_ticket_type(d['type'])
        if not d.get('approval_status'):
            d['approval_status'] = 'NONE'
        return d
    return JSONResponse({"error": "Not found"}, status_code=404)


@router.get("/api/agents/instructions/{gem_key}")
def get_agent_instruction_detail(gem_key: str):
    conn = get_db()
    row = conn.execute("SELECT sys_id, gem_key, title, description, instructions, sys_created_on, sys_updated_on FROM sys_gemini_instructions WHERE gem_key = ? OR sys_id = ?", (gem_key, gem_key)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return JSONResponse({"status": "error", "message": f"Instruction set for '{gem_key}' not found."}, status_code=404)


@router.get("/api/tickets/{ticket_id}/export")
@router.get("/api/tickets/{ticket_id}/export/{format}")
def export_ticket(ticket_id: str, format: str = "md"):
    format = str(format or "md").lower()
    if format not in ("md", "json", "pdf"):
        format = "md"
        
    conn = get_db()
    row = conn.execute("""
        SELECT sys_id, number as id, type, parent_sys_id, short_description as title, 
               description, work_notes, state as state_int, priority as p_int, 
               assigned_to, cmdb_ci as affected_ci, sys_created_on as created_at, 
               sys_updated_on as updated_at 
        FROM sovereign_tickets 
        WHERE number = ? OR sys_id = ?
    """, (ticket_id, ticket_id)).fetchone()
    
    if not row:
        conn.close()
        return JSONResponse({"error": "Ticket not found"}, status_code=404)
        
    d = dict(row)
    t_num = d['id']
    t_sys_id = d['sys_id']
    title = d['title'] or "Untitled Ticket"
    t_type = map_ticket_type(d['type'])
    status = map_state(d['state_int'])
    priority = map_priority(d['p_int'])
    assigned = d['assigned_to'] or "Unassigned"
    affected_ci = d['affected_ci'] or "None"
    created = d['created_at'] or "Unknown"
    updated = d['updated_at'] or "Unknown"
    desc = d['description'] or "*No description provided.*"
    work = d['work_notes'] or "*No work notes.*"
    
    # Fetch attachments
    att_rows = conn.execute("""
        SELECT file_name, file_path 
        FROM sys_attachment 
        WHERE table_name = 'sovereign_tickets' AND (table_sys_id = ? OR table_sys_id = ?)
    """, (t_sys_id, ticket_id)).fetchall()
    conn.close()
    
    att_list = ""
    if att_rows:
        for att in att_rows:
            att_list += f"- [{att['file_name']}]({att['file_path']})\n"
    else:
        att_list = "*No attachments.*"
        
    # Try to render inline walkthrough if available
    walkthrough_md = ""
    walkthrough_att = None
    for att in att_rows:
        fn = att['file_name'].lower()
        if fn.startswith('walkthrough_') and fn.endswith('.md'):
            walkthrough_att = att
            break

    if walkthrough_att:
        filename_on_disk = walkthrough_att['file_path'].replace('/attachments/', '')
        full_path = resolve_attachment_path(filename_on_disk)
        if full_path and os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    walkthrough_md = f.read()
                walkthrough_md = resolve_markdown_images(walkthrough_md, att_rows)
                walkthrough_md = resolve_markdown_links(walkthrough_md)
            except Exception as e:
                walkthrough_md = f"\n*Error loading walkthrough: {str(e)}*\n"
        
    # ── JSON export ────────────────────────────────────────────────────────────
    if format == "json":
        payload = {
            "ticket_id": t_num,
            "sys_id": t_sys_id,
            "title": title,
            "type": t_type,
            "status": status,
            "priority": priority,
            "assigned_to": assigned,
            "affected_ci": affected_ci,
            "created_at": created,
            "updated_at": updated,
            "description": desc,
            "work_notes": work,
            "attachments": [dict(r) for r in att_rows],
            "walkthrough": walkthrough_md
        }
        return Response(
            content=json.dumps(payload, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={t_num}_export.json"}
        )
        
    # Generate Markdown representation
    md_content = f"""# [{t_num}] {title}

| Attribute | Value |
| --- | --- |
| **Type** | {t_type} |
| **Status** | {status} |
| **Priority** | {priority} |
| **Assigned To** | {assigned} |
| **Affected CI** | {affected_ci} |
| **Created** | {created} |
| **Updated** | {updated} |

---

## 📝 Description

{desc}

---

## 📓 Work Notes

{work}

---

## 📎 Attachments

{att_list}
"""

    if walkthrough_md:
        md_content += f"""
---

## 🚀 Inline Walkthrough

{walkthrough_md}
"""


    # ── Markdown export ───────────────────────────────────────────────────────
    if format == "md":
        return Response(
            content=md_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={t_num}_export.md"}
        )
        
    # ── PDF export ────────────────────────────────────────────────────────────
    elif format == "pdf":
        import markdown
        # [Hoisted to header] import subprocess
        
        # Convert MD to HTML using markdown library
        body_html = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
        
        css_content = """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
        
        :root {
            --color-bg: #fafaf9;
            --color-text: #1c2e2c;
            --color-text-light: #445654;
            --color-primary: #0f766e;
            --color-primary-light: #f0fdfa;
            --color-accent: #b45309;
            --color-accent-light: #fef3c7;
            --color-border: #e2e8f0;
        }
        
        * {
            box-sizing: border-box;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        
        @page {
            size: letter;
            margin: 25mm 20mm 20mm 20mm;
            @bottom-right {
                content: counter(page);
                font-family: 'Outfit', sans-serif;
                font-size: 9pt;
                color: #889694;
            }
            @top-left {
                content: "Sovereign OS • Ticket Export Record";
                font-family: 'Outfit', sans-serif;
                font-size: 8pt;
                color: #889694;
                text-transform: uppercase;
                letter-spacing: 0.1em;
            }
        }
        
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            color: var(--color-text);
            background-color: var(--color-bg);
            line-height: 1.6;
            font-size: 11pt;
            margin: 0;
            padding: 0;
        }
        
        .content-container {
            padding: 0 10px;
        }
        
        h1, h2, h3, h4 {
            font-family: 'Outfit', sans-serif;
            color: #0f172a;
            font-weight: 700;
            margin-top: 1.6em;
            margin-bottom: 0.5em;
            page-break-after: avoid;
        }
        
        h1 {
            font-size: 22pt;
            line-height: 1.2;
            border-bottom: 3px solid var(--color-primary);
            padding-bottom: 8px;
            margin-top: 0;
            margin-bottom: 1em;
            text-transform: uppercase;
        }
        
        h2 {
            font-size: 13pt;
            border-left: 4px solid var(--color-primary);
            padding-left: 12px;
            color: var(--color-primary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 2em;
        }
        
        h3 {
            font-size: 11pt;
            color: var(--color-accent);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        p {
            margin-top: 0;
            margin-bottom: 1.2em;
            color: var(--color-text-light);
            text-align: justify;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5em 0;
            page-break-inside: avoid;
            font-size: 9.5pt;
        }
        
        th, td {
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid var(--color-border);
        }
        
        th {
            background-color: var(--color-primary-light);
            color: var(--color-primary);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 8.5pt;
            letter-spacing: 0.5px;
        }
        
        tr:nth-child(even) td {
            background-color: #fcfcfb;
        }
        
        blockquote {
            margin: 1.5em 0;
            padding: 15px 20px;
            background-color: #fef3c7;
            border-left: 5px solid #d97706;
            border-radius: 0 6px 6px 0;
            page-break-inside: avoid;
        }
        
        blockquote p {
            margin: 0;
            color: #78350f;
            font-weight: 500;
            font-size: 10pt;
        }
        
        pre {
            background-color: #0f172a;
            color: #38bdf8;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 9pt;
            line-height: 1.5;
            margin: 1.5em 0;
            border-left: 4px solid var(--color-accent);
        }
        
        code {
            font-family: 'JetBrains Mono', monospace;
            font-size: 90%;
            background-color: #f1f5f9;
            color: #0f766e;
            padding: 2px 4px;
            border-radius: 3px;
        }
        
        hr {
            border: 0;
            border-top: 1px dashed var(--color-border);
            margin: 2em 0;
        }
        """
        
        html_document = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                {css_content}
            </style>
        </head>
        <body>
            <div class="content-container">
                {body_html}
            </div>
        </body>
        </html>
        """
        
        # Post-process GitHub alert style blocks
        html_document = html_document.replace('<blockquote>\n<p>&gt; [!IMPORTANT]', '<blockquote style="background-color: #fef2f2; border-left-color: #ef4444;"><p style="color: #991b1b;"><strong>⚠️ IMPORTANT:</strong>')
        html_document = html_document.replace('<blockquote>\n<p>&gt; [!WARNING]', '<blockquote style="background-color: #fef2f2; border-left-color: #ef4444;"><p style="color: #991b1b;"><strong>⚠️ WARNING:</strong>')
        html_document = html_document.replace('<blockquote>\n<p>&gt; [!TIP]', '<blockquote style="background-color: #fef3c7; border-left-color: #d97706;"><p style="color: #78350f;"><strong>💡 TIP:</strong>')
        html_document = html_document.replace('<blockquote>\n<p>&gt; [!NOTE]', '<blockquote style="background-color: #eff6ff; border-left-color: #3b82f6;"><p style="color: #1e3a8a;"><strong>ℹ️ NOTE:</strong>')
        
        # Create temp files
        temp_dir = "/home/james/stacklabs/scratch"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        temp_html_path = os.path.join(temp_dir, f"ticket_{t_num}_temp.html")
        temp_pdf_path = os.path.join(temp_dir, f"ticket_{t_num}_temp.pdf")
        
        try:
            with open(temp_html_path, 'w', encoding='utf-8') as f:
                f.write(html_document)
                
            # Run Headless Chrome to compile PDF
            chrome_cmd = [
                "/snap/bin/chromium",
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--virtual-time-budget=10000",
                f"--print-to-pdf={temp_pdf_path}",
                f"file://{temp_html_path}"
            ]
            
            result = subprocess.run(chrome_cmd, capture_output=True, text=True)
            if not os.path.exists(temp_pdf_path):
                raise Exception(f"Chromium PDF generation failed (code {result.returncode}): {result.stderr or result.stdout}")
                
            with open(temp_pdf_path, 'rb') as f:
                pdf_data = f.read()
                
            return Response(
                content=pdf_data,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={t_num}_export.pdf"}
            )
        finally:
            if os.path.exists(temp_html_path):
                try: os.remove(temp_html_path)
                except: pass
            if os.path.exists(temp_pdf_path):
                try: os.remove(temp_pdf_path)
                except: pass


@router.api_route("/tickets/{ticket_id}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def get_flat_ticket_page(ticket_id: str):
    conn = get_db()
    row = conn.execute("""
        SELECT sys_id, number as id, type, parent_sys_id, short_description as title, 
               description, work_notes, state as state_int, priority as p_int, 
               assigned_to, cmdb_ci as affected_ci, sys_created_on as created_at, 
               sys_updated_on as updated_at 
        FROM sovereign_tickets 
        WHERE number = ? OR sys_id = ?
    """, (ticket_id, ticket_id)).fetchone()
    
    if not row:
        conn.close()
        return HTMLResponse("<h1>Ticket Not Found</h1>", status_code=404)
        
    d = dict(row)
    t_num = d['id']
    t_sys_id = d['sys_id']
    title = d['title'] or "Untitled Ticket"
    t_type = map_ticket_type(d['type'])
    status = map_state(d['state_int'])
    priority = map_priority(d['p_int'])
    assigned = d['assigned_to'] or "Unassigned"
    affected_ci = d['affected_ci'] or "None"
    created = d['created_at'] or "Unknown"
    updated = d['updated_at'] or "Unknown"
    desc = d['description'] or "*No description provided.*"
    work = d['work_notes'] or "*No work notes.*"
    
    # Fetch attachments
    att_rows = conn.execute("""
        SELECT file_name, file_path 
        FROM sys_attachment 
        WHERE table_name = 'sovereign_tickets' AND (table_sys_id = ? OR table_sys_id = ?)
    """, (t_sys_id, ticket_id)).fetchall()
    conn.close()
    
    att_html = ""
    if att_rows:
        for att in att_rows:
            att_html += f'<li><a href="{att["file_path"]}" target="_blank">📎 {att["file_name"]}</a></li>'
    else:
        att_html = '<li class="no-data">No attachments associated with this ticket.</li>'

    # Try to render inline walkthrough if available
    walkthrough_html = ""
    walkthrough_att = None
    for att in att_rows:
        fn = att['file_name'].lower()
        if fn.startswith('walkthrough_') and fn.endswith('.md'):
            walkthrough_att = att
            break

    if walkthrough_att:
        filename_on_disk = walkthrough_att['file_path'].replace('/attachments/', '')
        full_path = resolve_attachment_path(filename_on_disk)
        if full_path and os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    md_text = f.read()
                md_text = resolve_markdown_images(md_text, att_rows)
                md_text = resolve_markdown_links(md_text)
                walkthrough_html = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
            except Exception as e:
                walkthrough_html = f"<p class='error'>Error loading walkthrough: {str(e)}</p>"

    walkthrough_section_html = ""
    if walkthrough_html:
        walkthrough_section_html = f"""
      <div class="section">
        <h2>🚀 Inline Walkthrough</h2>
        <div class="walkthrough-body">
          {walkthrough_html}
        </div>
      </div>
"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[{t_num}] {title} - Sovereign SDLC</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-primary: #0b0d13;
      --bg-secondary: #121520;
      --bg-card: #161a29;
      --border: #2a2f3e;
      --border-glow: rgba(0, 180, 216, 0.4);
      --text-primary: #e2e8f0;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --amber: #f59e0b;
      --amber-dim: rgba(245, 158, 11, 0.3);
      --cyan: #00b4d8;
      --green: #10b981;
      --green-dim: rgba(16, 185, 129, 0.2);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: 'Outfit', sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.5;
      padding: 40px 20px;
    }}

    .container {{
      max-width: 800px;
      margin: 0 auto;
    }}

    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 16px;
    }}

    .back-link {{
      color: var(--text-secondary);
      text-decoration: none;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: color 0.15s;
    }}

    .back-link:hover {{
      color: var(--cyan);
    }}

    .actions {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .btn {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      padding: 8px 16px;
      border-radius: 4px;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }}

    .btn-export {{
      background: var(--green-dim);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: var(--green);
    }}

    .btn-export:hover {{
      background: rgba(16, 185, 129, 0.3);
      box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
    }}

    .ticket-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 32px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }}

    .ticket-header {{
      margin-bottom: 24px;
    }}

    .ticket-meta {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }}

    .ticket-id {{
      font-family: 'JetBrains Mono', monospace;
      font-weight: 700;
      color: var(--cyan);
      font-size: 14px;
      background: rgba(0, 180, 216, 0.1);
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid rgba(0, 180, 216, 0.2);
    }}

    .badge {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 3px;
    }}

    .badge-status {{
      background: rgba(245, 158, 11, 0.15);
      color: var(--amber);
      border: 1px solid var(--amber-dim);
    }}

    .badge-status.DONE {{
      background: rgba(16, 185, 129, 0.15);
      color: var(--green);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .badge-priority {{
      background: rgba(100, 116, 139, 0.15);
      color: var(--text-secondary);
      border: 1px solid var(--border);
    }}

    h1 {{
      font-size: 24px;
      font-weight: 600;
      color: #ffffff;
      line-height: 1.3;
    }}

    .metadata-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 20px;
      margin-bottom: 32px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
    }}

    .meta-item {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .meta-label {{
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 1px;
    }}

    .meta-val {{
      color: var(--text-primary);
      font-weight: 600;
    }}

    .section {{
      margin-bottom: 32px;
    }}

    .section h2 {{
      font-size: 11px;
      font-weight: 700;
      color: var(--cyan);
      text-transform: uppercase;
      letter-spacing: 1.5px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 6px;
    }}

    .section-body {{
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 20px;
      font-size: 14px;
      color: var(--text-primary);
      white-space: pre-wrap;
    }}

    .section-body.empty {{
      color: var(--text-muted);
      font-style: italic;
    }}

    .attachments-list {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .attachments-list li a {{
      color: var(--cyan);
      text-decoration: none;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: color 0.15s;
    }}

    .attachments-list li a:hover {{
      color: #ffffff;
      text-decoration: underline;
    }}

    .no-data {{
      color: var(--text-muted);
      font-style: italic;
      font-size: 13px;
    }}

    .walkthrough-body {{
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 24px;
      font-size: 14px;
      color: var(--text-primary);
      margin-top: 12px;
      line-height: 1.6;
    }}
    .walkthrough-body h1, .walkthrough-body h2, .walkthrough-body h3 {{
      color: var(--cyan);
      margin-top: 24px;
      margin-bottom: 12px;
      font-weight: 600;
    }}
    .walkthrough-body h1 {{
      font-size: 20px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 6px;
    }}
    .walkthrough-body h2 {{ font-size: 17px; }}
    .walkthrough-body h3 {{ font-size: 15px; }}
    .walkthrough-body p {{ margin-bottom: 16px; }}
    .walkthrough-body ul, .walkthrough-body ol {{
      margin-bottom: 16px;
      padding-left: 24px;
    }}
    .walkthrough-body li {{ margin-bottom: 6px; }}
    .walkthrough-body code {{
      font-family: 'JetBrains Mono', monospace;
      background: rgba(0, 180, 216, 0.1);
      color: var(--cyan);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 13px;
    }}
    .walkthrough-body pre {{
      background: #07090e;
      border: 1px solid var(--border);
      padding: 16px;
      border-radius: 6px;
      overflow-x: auto;
      margin-bottom: 16px;
    }}
    .walkthrough-body pre code {{
      background: none;
      color: var(--text-primary);
      padding: 0;
      font-size: 13px;
    }}
    .walkthrough-body img {{
      max-width: 100%;
      height: auto;
      border-radius: 6px;
      border: 1px solid var(--border);
      margin: 16px 0;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
    .walkthrough-body table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 16px;
    }}
    .walkthrough-body th, .walkthrough-body td {{
      border: 1px solid var(--border);
      padding: 8px 12px;
      text-align: left;
    }}
    .walkthrough-body th {{
      background: var(--bg-card);
      color: #ffffff;
    }}
  </style>
</head>
<body>

  <div class="container">
    <div class="header">
      <a href="http://clio.taila01894.ts.net:3029" class="back-link">← Mobile Console</a>
      <div class="actions" style="display: flex; gap: 8px;">
        <a href="http://clio.taila01894.ts.net:3029/?ticket={t_num}" class="btn btn-export" style="background-color: #0284c7; border-color: #0284c7; color: #ffffff;">📱 Mobile App</a>
        <a href="/api/tickets/{t_num}" class="btn btn-export" style="background-color: #334155; border-color: #334155; color: #ffffff;">⚡ JSON</a>
        <a href="/api/tickets/{t_num}/export/md" class="btn btn-export" style="background-color: #0f766e; border-color: #0f766e; color: #ffffff;">📝 MD</a>
        <a href="/api/tickets/{t_num}/export/pdf" class="btn btn-export" style="background-color: #b45309; border-color: #b45309; color: #ffffff;">📕 PDF</a>
      </div>
    </div>

    <div class="ticket-card">
      <div class="ticket-header">
        <div class="ticket-meta">
          <span class="ticket-id">{t_num}</span>
          <span class="badge badge-type">{t_type}</span>
          <span class="badge badge-status {status}">{status}</span>
          <span class="badge badge-priority">{priority}</span>
        </div>
        <h1>{title}</h1>
      </div>

      <div class="metadata-grid">
        <div class="meta-item">
          <span class="meta-label">Assigned To</span>
          <span class="meta-val">{assigned}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Affected CI</span>
          <span class="meta-val">{affected_ci}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Created At</span>
          <span class="meta-val">{created}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Updated At</span>
          <span class="meta-val">{updated}</span>
        </div>
      </div>

      <div class="section">
        <h2>📝 Description</h2>
        <div class="section-body">{desc}</div>
      </div>

      <div class="section">
        <h2>📓 Work Notes</h2>
        <div class="section-body {"empty" if not d['work_notes'] else ""}">{work}</div>
      </div>

      {walkthrough_section_html}

      <div class="section">
        <h2>📎 Attachments</h2>
        <ul class="attachments-list">
          {att_html}
        </ul>
      </div>
    </div>
  </div>

</body>
</html>
"""
    return HTMLResponse(content=html_content)


@router.put("/api/tickets/{ticket_id}")
@router.patch("/api/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, request: Request):
    data = await request.json()
    conn = None
    try:
        conn = get_db()
        
        # Check existing ticket & enforce Rule IV.2.b governance gate
        t_row = conn.execute("SELECT sys_id, number, type, cmdb_ci, short_description, description, state FROM sovereign_tickets WHERE number = ? OR sys_id = ?", (ticket_id, ticket_id)).fetchone()
        if not t_row:
            # Rule IV.17 (The File-First GitOps Mandate — Post-Execution Projection):
            # Under File-First GitOps, work orders are executed without pre-execution SQLite staging.
            # Project ticket record upon resolution via PUT /api/tickets/{ticket_id}
            sys_id = uuid.uuid4().hex
            ui_type = data.get('ticket_type', 'Enhancement' if 'ENHC' in ticket_id.upper() else 'Work Order' if ticket_id.upper().startswith('WO') else 'Story')
            db_type = reverse_map_ticket_type(ui_type)
            target_state = reverse_map_state(data.get('status', 'DONE'))
            target_prio = reverse_map_priority(data.get('priority', 'P3'))
            now_iso = datetime.now().isoformat()
            target_title = data.get('title') or data.get('short_description') or ticket_id
            target_desc = data.get('description') or target_title
            target_ci = data.get('affected_ci') or data.get('cmdb_ci') or 'sovereign_knot_core'
            target_assigned = data.get('assigned_to', 'clio')
            target_work_notes = data.get('work_notes', '')

            conn.execute("""
                INSERT INTO sovereign_tickets (
                    sys_id, number, type, parent_sys_id, short_description, 
                    description, work_notes, state, priority, assigned_to, 
                    cmdb_ci, sys_created_on, sys_updated_on
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sys_id,
                ticket_id,
                db_type,
                data.get('parent_sys_id'),
                target_title,
                target_desc,
                target_work_notes,
                target_state,
                target_prio,
                target_assigned,
                target_ci,
                now_iso,
                now_iso
            ))
            conn.commit()
            t_row = conn.execute("SELECT sys_id, number, type, cmdb_ci, short_description, description, state FROM sovereign_tickets WHERE number = ? OR sys_id = ?", (ticket_id, ticket_id)).fetchone()
            
        status_val = data.get('status') or data.get('state') or data.get('state_int')
        if status_val is not None:
            target_state = reverse_map_state(status_val)
            if target_state in (4, 5):
                ticket_eval = dict(t_row)
                if 'affected_ci' in data:
                    ticket_eval['affected_ci'] = data['affected_ci']
                if 'title' in data:
                    ticket_eval['short_description'] = data['title']
                if 'description' in data:
                    ticket_eval['description'] = data['description']
                    
                if 'work_notes' in data:
                    ticket_eval['work_notes'] = data['work_notes']
                    
                if is_ui_ticket(ticket_eval):
                    twin_ok, twin_detail = has_verified_visual_twin(conn, t_row['sys_id'], t_row['number'], ticket_data=ticket_eval, return_detail=True)
                    if not twin_ok:
                        return JSONResponse(
                            status_code=422,
                            content={
                                "error": "SDLC_GOVERNANCE_GATE_VIOLATION",
                                "code": "RULE_IV_2_B",
                                "ticket_id": ticket_id,
                                "ticket_number": t_row['number'],
                                "detail": twin_detail
                            }
                        )
                        
        fields = []
        params = []
        
        if 'number' in data:
            fields.append("number = ?")
            params.append(data['number'])
        if 'title' in data:
            fields.append("short_description = ?")
            params.append(data['title'])
        if 'description' in data:
            fields.append("description = ?")
            params.append(data['description'])
        if 'work_notes' in data:
            fields.append("work_notes = ?")
            params.append(data['work_notes'])
        if status_val is not None:
            fields.append("state = ?")
            params.append(reverse_map_state(status_val))
        if 'priority' in data:
            fields.append("priority = ?")
            params.append(reverse_map_priority(data['priority']))
        if 'assigned_to' in data:
            fields.append("assigned_to = ?")
            params.append(data['assigned_to'])
        if 'affected_ci' in data:
            fields.append("cmdb_ci = ?")
            params.append(data['affected_ci'])
        if 'ticket_type' in data:
            fields.append("type = ?")
            params.append(reverse_map_ticket_type(data['ticket_type']))
        if 'parent_sys_id' in data:
            fields.append("parent_sys_id = ?")
            params.append(data['parent_sys_id'])
        if 'epic_id' in data:
            fields.append("epic_id = ?")
            params.append(data['epic_id'])
        if 'feature_id' in data:
            fields.append("feature_id = ?")
            params.append(data['feature_id'])
            
        fields.append("sys_updated_on = ?")
        params.append(datetime.now().isoformat())
            
        if not fields:
            return JSONResponse({"error": "No valid fields"}, status_code=400)
            
        params.append(ticket_id)
        params.append(ticket_id)
        conn.execute(f"UPDATE sovereign_tickets SET {', '.join(fields)} WHERE number = ? OR sys_id = ?", params)
        conn.commit()
    finally:
        if conn:
            conn.close()

    # Determine specific audit event type
    audit_event = "ticket.update"
    if 'status' in data:
        st = reverse_map_state(data['status'])
        if st in (4, 5):
            audit_event = "ticket.resolve"
        elif st == 2:
            audit_event = "ticket.claim"
    elif data.get('request_approval'):
        audit_event = "ticket.stage"

    audit_payload = {
        "number": t_row['number'] if t_row else ticket_id,
        "ticket_id": ticket_id,
        "event": audit_event,
        "updated_fields": [k for k in data.keys() if k != 'work_notes'],
    }
    if 'status' in data:
        audit_payload["status"] = data['status']
        if t_row:
            audit_payload["previous_state"] = t_row['state']
    if 'work_notes' in data and data['work_notes']:
        audit_payload["work_notes_snippet"] = str(data['work_notes'])[:256]

    log_audit_chain_event(audit_event, audit_payload)
        
    # Trigger lightweight sync in background if ticket resolved
    if 'status' in data and reverse_map_state(data['status']) == 4:
        # [Hoisted to header] import subprocess
        try:
            subprocess.Popen(["/bin/bash", "/home/james/stacklabs/scripts/sync_lightweight.sh"])
        except Exception as e:
            print(f"[!] Failed to launch background lightweight sync: {e}")
            
    return {"id": ticket_id, "status": "updated"}


@router.delete("/api/tickets/{ticket_id}")
def delete_ticket(ticket_id: str):
    conn = None
    try:
        conn = get_db()
        conn.execute("DELETE FROM sovereign_tickets WHERE number = ? OR sys_id = ?", (ticket_id, ticket_id))
        conn.commit()
    finally:
        if conn:
            conn.close()
    return {"id": ticket_id, "status": "deleted"}


@router.put("/api/sdlc/initiatives/{initiative_id}")
async def update_initiative(initiative_id: str, request: Request):
    data = await request.json()
    conn = get_db()
    fields = []
    params = []
    for k in ["name", "code", "description", "owner", "status", "icon", "color"]:
        if k in data:
            fields.append(f"{k} = ?")
            params.append(data[k])
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(initiative_id)
    conn.execute(f"UPDATE sdlc_initiatives SET {', '.join(fields)} WHERE initiative_id = ?", params)
    conn.commit()
    conn.close()
    return {"initiative_id": initiative_id, "status": "updated"}


@router.delete("/api/sdlc/initiatives/{initiative_id}")
def delete_initiative(initiative_id: str):
    conn = get_db()
    conn.execute("DELETE FROM sdlc_initiatives WHERE initiative_id = ?", (initiative_id,))
    conn.commit()
    conn.close()
    return {"initiative_id": initiative_id, "status": "deleted"}


@router.get("/api/sdlc/epics/{epic_id}")
def get_epic_detail(epic_id: int):
    conn = get_db()
    epic_row = conn.execute("SELECT * FROM v_sdlc_epic_rollup WHERE epic_id = ?", (epic_id,)).fetchone()
    if not epic_row:
        conn.close()
        return JSONResponse({"error": "Epic not found"}, status_code=404)
        
    epic_dict = dict(epic_row)
    
    # Child features
    feat_rows = conn.execute("""
        SELECT f.*,
               COUNT(t.number) as total_tickets,
               SUM(CASE WHEN t.state IN (4, 5) THEN 1 ELSE 0 END) as completed_tickets
        FROM sdlc_features f
        LEFT JOIN sovereign_tickets t ON t.feature_id = f.feature_id
        WHERE f.epic_id = ?
        GROUP BY f.feature_id
        ORDER BY f.feature_id ASC
    """, (epic_id,)).fetchall()
    epic_dict["features"] = [dict(f) for f in feat_rows]
    
    # Linked tickets
    ticket_rows = conn.execute("""
        SELECT t.sys_id, t.number as id, t.type, t.short_description as title, 
               t.description, t.work_notes, t.state as state_int, t.priority as p_int, 
               t.assigned_to, t.cmdb_ci as affected_ci, t.feature_id,
               f.title as feature_title,
               t.sys_created_on as created_at, t.sys_updated_on as updated_at
        FROM sovereign_tickets t
        LEFT JOIN sdlc_features f ON f.feature_id = t.feature_id
        WHERE t.epic_id = ?
        ORDER BY t.sys_created_on DESC
    """, (epic_id,)).fetchall()
    
    tickets = []
    for r in ticket_rows:
        td = dict(r)
        td['status'] = map_state(td['state_int'])
        td['priority'] = map_priority(td['p_int'])
        td['ticket_type'] = map_ticket_type(td['type'])
        tickets.append(td)
    epic_dict["tickets"] = tickets
    
    conn.close()
    return epic_dict


@router.put("/api/sdlc/epics/{epic_id}")
async def update_epic(epic_id: int, request: Request):
    data = await request.json()
    conn = get_db()
    fields = []
    params = []
    for k in ["initiative_id", "epic_key", "epic_name", "description", "owner", "status", "health", "color", "risk_level", "business_value", "architecture_spec_url", "target_date"]:
        if k in data:
            fields.append(f"{k} = ?")
            params.append(data[k])
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(epic_id)
    conn.execute(f"UPDATE sovereign_epics SET {', '.join(fields)} WHERE epic_id = ?", params)
    conn.commit()
    conn.close()
    return {"epic_id": epic_id, "status": "updated"}


@router.delete("/api/sdlc/epics/{epic_id}")
def delete_epic(epic_id: int):
    conn = get_db()
    conn.execute("DELETE FROM sovereign_epics WHERE epic_id = ?", (epic_id,))
    # Unset epic_id on tickets
    conn.execute("UPDATE sovereign_tickets SET epic_id = NULL WHERE epic_id = ?", (epic_id,))
    conn.commit()
    conn.close()
    return {"epic_id": epic_id, "status": "deleted"}


@router.put("/api/sdlc/features/{feature_id}")
async def update_feature(feature_id: int, request: Request):
    data = await request.json()
    conn = get_db()
    fields = []
    params = []
    for k in ["epic_id", "feature_key", "title", "description", "status", "priority", "owner", "acceptance_criteria"]:
        if k in data:
            fields.append(f"{k} = ?")
            params.append(data[k])
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(feature_id)
    conn.execute(f"UPDATE sdlc_features SET {', '.join(fields)} WHERE feature_id = ?", params)
    conn.commit()
    conn.close()
    return {"feature_id": feature_id, "status": "updated"}


@router.delete("/api/sdlc/features/{feature_id}")
def delete_feature(feature_id: int):
    conn = get_db()
    conn.execute("DELETE FROM sdlc_features WHERE feature_id = ?", (feature_id,))
    conn.execute("UPDATE sovereign_tickets SET feature_id = NULL WHERE feature_id = ?", (feature_id,))
    conn.commit()
    conn.close()
    return {"feature_id": feature_id, "status": "deleted"}


@router.delete("/api/sdlc/dependencies/{dependency_id}")
def delete_dependency(dependency_id: int):
    conn = get_db()
    conn.execute("DELETE FROM sovereign_ticket_dependencies WHERE dependency_id = ?", (dependency_id,))
    conn.commit()
    conn.close()
    return {"dependency_id": dependency_id, "status": "deleted"}


@router.post("/api/v1/approvals/{appr_id}/action")
def execute_approval_action(appr_id: str, req: ApprovalActionRequest):
    conn = get_db()
    c = conn.cursor()
    try:
        if req.action.upper() in ["EXECUTE", "AUTHORIZE"]:
            c.execute("""
                UPDATE sys_approval_queue 
                SET state = 'Executed', auth_level = 'omega=1', sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ? OR task_id = ?
            """, (appr_id, appr_id))
        else:
            c.execute("""
                UPDATE sys_approval_queue 
                SET state = 'Dismissed', sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ? OR task_id = ?
            """, (appr_id, appr_id))
        conn.commit()
        return {"status": "SUCCESS", "action": req.action, "sys_id": appr_id}
    finally:
        conn.close()


@router.put("/api/approvals/{appr_id}")
def update_approval_record(appr_id: str, req: ApprovalUpdateRequest):
    conn = get_db()
    c = conn.cursor()
    try:
        updates = ["sys_updated_on = CURRENT_TIMESTAMP"]
        params = []
        if req.state is not None:
            updates.append("state = ?")
            params.append(req.state)
        if req.auth_level is not None:
            updates.append("auth_level = ?")
            params.append(req.auth_level)
        if req.plan_markdown is not None:
            updates.append("plan_markdown = ?")
            params.append(req.plan_markdown)
        
        params.extend([appr_id, appr_id])
        query = f"UPDATE sys_approval_queue SET {', '.join(updates)} WHERE sys_id = ? OR task_id = ?"
        c.execute(query, tuple(params))
        conn.commit()
        return {"status": "SUCCESS", "sys_id": appr_id, "updated": True}
    finally:
        conn.close()


@router.get("/api/recon/prospects/{slug}")
def get_recon_prospect_detail_endpoint(slug: str):
    """Retrieve prospect details, runs, and keyword results from recon_sentinel.db."""
    if not os.path.exists(RECON_DB_PATH):
        raise HTTPException(status_code=404, detail="Recon database not found")
    with sqlite3.connect(RECON_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        prospect = conn.execute("SELECT * FROM prospects WHERE prospect_id = ?", (slug,)).fetchone()
        if not prospect:
            raise HTTPException(status_code=404, detail=f"Prospect '{slug}' not found")
        runs = conn.execute("SELECT * FROM serp_audit_runs WHERE prospect_id = ? ORDER BY executed_at DESC", (slug,)).fetchall()
        keywords = conn.execute("SELECT * FROM target_keywords WHERE prospect_id = ?", (slug,)).fetchall()
        results = conn.execute(
            """
            SELECT skr.*, tk.keyword, tk.estimated_ticket_value, tk.intent_category
            FROM serp_keyword_results skr
            JOIN target_keywords tk ON skr.keyword_id = tk.keyword_id
            WHERE tk.prospect_id = ?
            ORDER BY skr.created_at DESC
            """,
            (slug,)
        ).fetchall()
        return {
            "prospect": dict(prospect),
            "runs": [dict(r) for r in runs],
            "keywords": [dict(k) for k in keywords],
            "results": [dict(res) for res in results]
        }

