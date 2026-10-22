"""
Sovereign OS: Enterprise REST API Client SDK
Path: /home/james/stacklabs/scripts/core/api_client.py

Unified, high-performance Python REST client for querying and mutating Sovereign OS state.
Directs all traffic to Clio's live FastAPI endpoints on loopback (Port 8095, Port 8090, Port 8082).
Eliminates raw sqlite3.connect() calls and prevents SQLite file-lock contention.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

PORTAL_API_BASE = os.getenv("SOVEREIGN_PORTAL_API", "http://127.0.0.1:8095")
CORE_API_BASE = os.getenv("SOVEREIGN_CORE_API", "http://127.0.0.1:8090")
CMDB_API_BASE = os.getenv("SOVEREIGN_CMDB_API", "http://127.0.0.1:8082")
RELAY_API_BASE = os.getenv("SOVEREIGN_RELAY_API", "http://127.0.0.1:8000")

TIMEOUT_SECONDS = 5.0

def _http_request(url: str, method: str = "GET", data: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None, max_retries: int = 3) -> Any:
    """Internal helper to execute JSON HTTP requests with connection pooling, timeouts, and exponential backoff retries."""
    import time
    headers = {
        "Accept": "application/json",
        "User-Agent": "Sovereign-ApiClient/1.0"
    }
    encoded_data = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        encoded_data = json.dumps(data).encode("utf-8")

    req_timeout = timeout or TIMEOUT_SECONDS
    last_error = None

    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=req_timeout) as response:
                if response.status in (200, 201, 202, 204):
                    body = response.read().decode("utf-8")
                    return json.loads(body) if body else {}
                raise RuntimeError(f"HTTP {response.status} from {url}")
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500 and e.code != 429:
                error_body = e.read().decode("utf-8") if e.fp else ""
                raise RuntimeError(f"HTTP {e.code} Error from {url}: {error_body}")
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(0.2 * (2 ** attempt))
        except urllib.error.URLError as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(0.2 * (2 ** attempt))
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(0.2 * (2 ** attempt))

    if isinstance(last_error, urllib.error.HTTPError):
        error_body = last_error.read().decode("utf-8") if last_error.fp else ""
        raise RuntimeError(f"HTTP {last_error.code} Error from {url} after {max_retries} retries: {error_body}")
    elif isinstance(last_error, urllib.error.URLError):
        raise ConnectionError(f"Failed to connect to FastAPI endpoint at {url} after {max_retries} retries: {last_error.reason}")
    elif last_error is not None:
        raise RuntimeError(f"Request failed to {url} after {max_retries} retries: {last_error}")

# ==============================================================================
# SDLC TICKETS & APPROVALS (PORT 8095)
# ==============================================================================

def health_check() -> Dict[str, Any]:
    """Check SDLC Portal FastAPI operational health on Port 8095."""
    url = f"{PORTAL_API_BASE}/api/health"
    return _http_request(url, method="GET")


def get_tickets(state_int: Optional[List[int]] = None, priority: Optional[int] = None, ci: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all tickets from the SDLC FastAPI backend with optional filtering."""
    url = f"{PORTAL_API_BASE}/api/tickets"
    tickets = _http_request(url, method="GET")
    if not isinstance(tickets, list):
        return []

    filtered = []
    for t in tickets:
        if state_int is not None and t.get("state_int") not in state_int:
            continue
        if priority is not None and t.get("p_int") != priority:
            continue
        if ci is not None:
            affected_ci = (t.get("affected_ci") or "").lower()
            title = (t.get("title") or "").lower()
            if ci.lower() not in affected_ci and ci.lower() not in title:
                continue
        filtered.append(t)
    return filtered

def get_open_tickets(ci: Optional[str] = None, priority: Optional[int] = None) -> List[Dict[str, Any]]:
    """Convenience helper to retrieve Open (1) and In-Progress (2) tickets."""
    return get_tickets(state_int=[1, 2], priority=priority, ci=ci)

def get_ticket(ticket_id: str, default: Any = None) -> Optional[Dict[str, Any]]:
    """Fetch single ticket detail by ID or Number. Returns None if 404 Not Found."""
    url = f"{PORTAL_API_BASE}/api/tickets/{urllib.parse.quote(ticket_id)}"
    try:
        return _http_request(url, method="GET")
    except RuntimeError as e:
        if "HTTP 404" in str(e):
            return default
        raise

def get_next_number(category: str = "WO", increment: bool = False) -> Dict[str, Any]:
    """Retrieve next auto-number for a ticket category (e.g. WO, STRY, INC, DFCT)."""
    params = urllib.parse.urlencode({"category": category, "increment": str(increment).lower()})
    url = f"{PORTAL_API_BASE}/api/tickets/next_number?{params}"
    return _http_request(url, method="GET")

def get_next_hybrid_number(category: str = "WO", slug: str = "", increment: bool = True) -> str:
    """Convenience helper to retrieve and increment next hybrid ticket identifier (e.g. WO0010097-MY-TASK)."""
    params = urllib.parse.urlencode({
        "category": category,
        "slug": slug,
        "increment": str(increment).lower()
    })
    url = f"{PORTAL_API_BASE}/api/tickets/next_number?{params}"
    res = _http_request(url, method="GET")
    return res.get("hybrid_id") or res.get("next_number")

def create_ticket(title: str, ticket_type: str = "Story", description: str = "", 
                  priority: str = "P3", status: str = "PLANNING", 
                  assigned_to: str = "james", affected_ci: str = "01_Sovereign_Portal",
                  work_notes: str = "", number: Optional[str] = None) -> Dict[str, Any]:
    """Create a new SDLC ticket through the FastAPI backend."""
    url = f"{PORTAL_API_BASE}/api/tickets"
    payload = {
        "title": title,
        "ticket_type": ticket_type,
        "description": description,
        "priority": priority,
        "status": status,
        "assigned_to": assigned_to,
        "affected_ci": affected_ci,
        "work_notes": work_notes
    }
    if number:
        payload["number"] = number
    return _http_request(url, method="POST", data=payload)

def update_ticket(ticket_id: str, status: Optional[Union[str, Dict[str, Any]]] = None, work_notes: Optional[str] = None,
                  priority: Optional[str] = None, assigned_to: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Update an existing SDLC ticket's state, work notes, or priority via FastAPI."""
    url = f"{PORTAL_API_BASE}/api/tickets/{urllib.parse.quote(ticket_id)}"
    payload = {}
    if isinstance(status, dict):
        payload.update(status)
    elif status is not None:
        payload["status"] = status
    if work_notes is not None:
        payload["work_notes"] = work_notes
    if priority is not None:
        payload["priority"] = priority
    if assigned_to is not None:
        payload["assigned_to"] = assigned_to
    payload.update(kwargs)
    return _http_request(url, method="PUT", data=payload)

def resolve_ticket(ticket_id: str, resolution_notes: str) -> Dict[str, Any]:
    """Resolve an SDLC ticket (state = 4 / DONE) with comprehensive work notes."""
    return update_ticket(ticket_id, status="DONE", work_notes=resolution_notes)

def delete_ticket(ticket_id: str) -> Dict[str, Any]:
    """Delete an SDLC ticket via FastAPI DELETE endpoint."""
    url = f"{PORTAL_API_BASE}/api/tickets/{urllib.parse.quote(ticket_id)}"
    return _http_request(url, method="DELETE")

def audit_append(event_type: str, payload: Dict[str, Any], signature_key: Optional[str] = None) -> Dict[str, Any]:
    """Append a cryptographic event to the Sovereign Merkle Audit Chain."""
    url = f"{PORTAL_API_BASE}/api/audit/append"
    body = {"event_type": event_type, "payload": payload}
    if signature_key:
        body["signature_key"] = signature_key
    return _http_request(url, method="POST", data=body)

def audit_verify(from_seq: int = 1, to_seq: Optional[int] = None) -> Dict[str, Any]:
    """Verify cryptographic integrity of the Sovereign Merkle Audit Chain."""
    params = [f"from_seq={from_seq}"]
    if to_seq is not None:
        params.append(f"to_seq={to_seq}")
    url = f"{PORTAL_API_BASE}/api/audit/verify?{'&'.join(params)}"
    return _http_request(url, method="GET")

def audit_latest() -> Dict[str, Any]:
    """Retrieve the latest tip and sequence of the Sovereign Merkle Audit Chain."""
    url = f"{PORTAL_API_BASE}/api/audit/latest"
    return _http_request(url, method="GET")

def audit_entries(from_seq: int = 1, to_seq: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve audit chain entries in sequence order."""
    params = [f"from_seq={from_seq}", f"limit={limit}"]
    if to_seq is not None:
        params.append(f"to_seq={to_seq}")
    url = f"{PORTAL_API_BASE}/api/audit/entries?{'&'.join(params)}"
    return _http_request(url, method="GET")

def get_ticket_attachments(ticket_id: str) -> List[Dict[str, Any]]:
    """Retrieve all attachments bound to an SDLC ticket."""
    url = f"{PORTAL_API_BASE}/api/tickets/{urllib.parse.quote(ticket_id)}/attachments"
    return _http_request(url, method="GET")

def upload_ticket_attachment(ticket_id: str, file_path: str, filename: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    """Upload a file attachment to an SDLC ticket via multipart form-data."""
    url = f"{PORTAL_API_BASE}/api/tickets/{urllib.parse.quote(ticket_id)}/attachments"
    actual_filename = filename or os.path.basename(file_path)
    with open(file_path, "rb") as f:
        files = {"file": (actual_filename, f)}
        data = {"description": description} if description else {}
        try:
            import httpx
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, files=files, data=data)
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"HTTP {resp.status_code} from {url}: {resp.text}")
                return resp.json()
        except ImportError:
            import requests
            resp = requests.post(url, files=files, data=data, timeout=30.0)
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"HTTP {resp.status_code} from {url}: {resp.text}")
            return resp.json()

def delete_ticket_attachment(ticket_id: str, attachment_sys_id: str) -> Dict[str, Any]:
    """Delete an attachment from a ticket."""
    url = f"{PORTAL_API_BASE}/api/tickets/{urllib.parse.quote(ticket_id)}/attachments/{urllib.parse.quote(attachment_sys_id)}"
    return _http_request(url, method="DELETE")

def capture_and_upload_ticket_twin(
    ticket_id: str,
    url: str,
    click: Optional[str] = None,
    width: int = 1920,
    height: int = 1080,
    wait_ms: int = 3000,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes headless Playwright live browser capture from node Pegasus (100.96.77.20),
    validates KI-095 viewport compliance, and uploads the verified twin attachment to the ticket.
    Enforces Governance Invariant Rule IV.2.b.
    """
    from scripts.pegasus_sentry_client import run_sentry
    
    clean_fn = filename or f"pegasus_visual_twin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    if not clean_fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        clean_fn += ".png"
    if not any(k in clean_fn.lower() for k in ["pegasus", "visual_twin", "playwright", "live_uat"]):
        clean_fn = f"pegasus_visual_twin_{clean_fn}"
        
    local_path = f"/home/james/sovereign_inbox/tickets/{ticket_id}/mockups/{clean_fn}"
    report = run_sentry(url, local_path, width=width, height=height, wait_ms=wait_ms, click=click)
    if not report or not report.get("local_screenshot") or not os.path.exists(local_path):
        raise RuntimeError(f"Pegasus Playwright capture failed for URL {url}")
        
    upload_res = upload_ticket_attachment(ticket_id, local_path, filename=clean_fn)
    return {
        "status": "success",
        "ticket_id": ticket_id,
        "filename": clean_fn,
        "local_path": local_path,
        "ki095_compliant": report.get("ki095_compliant", False),
        "report": report,
        "attachment": upload_res
    }


def get_pending_approvals() -> List[Dict[str, Any]]:
    """Retrieve all pending JIT approval records."""
    url = f"{PORTAL_API_BASE}/api/v1/approvals/pending"
    data = _http_request(url, method="GET")
    return data.get("approvals", [])

def execute_approval_action(appr_id: str, action: str = "EXECUTE") -> Dict[str, Any]:
    """Reconcile or action an approval record via FastAPI on Port 8095."""
    url = f"{PORTAL_API_BASE}/api/v1/approvals/{urllib.parse.quote(appr_id)}/action"
    return _http_request(url, method="POST", data={"action": action})

# ==============================================================================
# IDEA & INNOVATION INCUBATOR QUEUE (PORT 8095)
# ==============================================================================

def get_ideas(status: Optional[str] = None, priority: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all concepts and mashups currently in the Idea Incubator queue."""
    url = f"{PORTAL_API_BASE}/api/ideas"
    return _http_request(url, method="GET")

def create_idea(title: str, description: str, priority: str = "P3", 
                affected_ci: str = "19_FanStackArena", work_notes: str = "") -> Dict[str, Any]:
    """Stage a new concept or R&D mashup into the Idea Incubator queue."""
    url = f"{PORTAL_API_BASE}/api/tickets"
    payload = {
        "title": title,
        "ticket_type": "IDEA",
        "description": description,
        "priority": priority,
        "status": "PLANNING",
        "assigned_to": "james",
        "affected_ci": affected_ci,
        "work_notes": work_notes
    }
    return _http_request(url, method="POST", data=payload)

def promote_idea(idea_id: str, target_type: str = "STRY", priority: int = 2) -> Dict[str, Any]:
    """Promote an Idea Incubator concept into an active Work Order or Story in the operational sprint backlog."""
    url = f"{PORTAL_API_BASE}/api/ideas/{urllib.parse.quote(idea_id)}/promote"
    payload = {
        "target_type": target_type,
        "priority": priority
    }
    return _http_request(url, method="POST", data=payload)

# ==============================================================================
# CMDB CONFIGURATION ITEMS & TELEMETRY (PORT 8082 / PORT 8095)
# ==============================================================================

def get_cmdb_cis() -> List[Dict[str, Any]]:
    """Retrieve all active Configuration Items from the CMDB service."""
    url = f"{PORTAL_API_BASE}/api/cmdb/cis"
    return _http_request(url, method="GET")

# ==============================================================================
# PERSONAS & FANSTACK DISCOURSE (PORT 8095)
# ==============================================================================

def get_all_personas() -> List[Dict[str, Any]]:
    """Retrieve all registered AI personas and advocates."""
    url = f"{PORTAL_API_BASE}/api/all_personas"
    data = _http_request(url, method="GET")
    return data.get("personas", []) if isinstance(data, dict) else data

def get_personas_by_team(team: str) -> List[Dict[str, Any]]:
    """Retrieve active personas belonging to a specific team (e.g. 'NYM', 'SD', 'COL')."""
    personas = get_all_personas()
    return [p for p in personas if (p.get("team") or "").upper() == team.upper()]

def get_persona(user_name: str) -> Dict[str, Any]:
    """Retrieve single persona profile by user_name."""
    url = f"{PORTAL_API_BASE}/api/persona/{urllib.parse.quote(user_name)}"
    return _http_request(url, method="GET")

def update_persona(user_name: str, **kwargs) -> Dict[str, Any]:
    """Update persona profile fields (system_prompt, deep_lore, governance, team, etc.)."""
    url = f"{PORTAL_API_BASE}/api/persona/update"
    payload = {"name": user_name, "user_name": user_name, **kwargs}
    return _http_request(url, method="POST", data=payload)

def purge_corrupt_ledger(persona_id: str, game_pk: str) -> Dict[str, Any]:
    """Purge corrupt short memory fragments for a persona in a game room."""
    url = f"{PORTAL_API_BASE}/api/persona/ledger/purge_corrupt?persona_id={urllib.parse.quote(persona_id)}&game_pk={urllib.parse.quote(game_pk)}"
    return _http_request(url, method="POST")

def get_persona_lookbook(advocate: str) -> Dict[str, Any]:
    """Retrieve full 22-shot pose catalog, shot keys, and active sprite state for an advocate."""
    url = f"{CORE_API_BASE}/api/persona/lookbook/{urllib.parse.quote(advocate)}"
    return _http_request(url, method="GET")

def set_persona_active_pose(advocate: str, pose_key: str, room: Optional[str] = None) -> Dict[str, Any]:
    """Dynamically set the active reaction sprite for an advocate across live game rooms."""
    url = f"{CORE_API_BASE}/api/persona/active_pose"
    payload = {"advocate": advocate, "pose_key": pose_key, "room": room}
    return _http_request(url, method="POST", data=payload)

def generate_persona_lookbook(advocate_id: str, preset: str = "full22", shot_selection: Optional[List[str]] = None) -> Dict[str, Any]:
    """Trigger lookbook seeder generation pipeline."""
    url = f"{CORE_API_BASE}/api/persona/lookbook/generate"
    payload = {"advocate_id": advocate_id, "preset": preset, "shot_selection": shot_selection}
    return _http_request(url, method="POST", data=payload)

def sync_advocate_assets() -> Dict[str, Any]:
    """Synchronize all advocate multi-pose assets, lookbooks, and authentic avatar PNGs across frontends and database."""
    url = f"{PORTAL_API_BASE}/api/persona/sync_advocate_assets"
    return _http_request(url, method="POST")


def forge_wildcard_advocate(
    name: str,
    concept: str,
    team_tag: Optional[str] = None,
    visual_style: str = "2D_ORGANIC_TOON_CARTOON",
    rivalry_target_handle: Optional[str] = None,
    generate_poses: bool = True,
    color: Optional[str] = None,
    cadence: str = "pacer",
    boggs_level: int = 2,
    rooms: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Trigger the Wildcard Advocate Forge asynchronous background service via FastAPI on Port 8095."""
    url = f"{PORTAL_API_BASE}/api/advocates/wildcard_forge"
    payload = {
        "name": name,
        "concept": concept,
        "team_tag": team_tag,
        "visual_style": visual_style,
        "rivalry_target_handle": rivalry_target_handle,
        "generate_poses": generate_poses,
        "color": color,
        "cadence": cadence,
        "boggs_level": boggs_level,
        "rooms": rooms or []
    }
    return _http_request(url, method="POST", data=payload)


def get_advocate_forge_status(task_id: str) -> Dict[str, Any]:
    """Query the status of an asynchronous Wildcard Advocate Forge task via FastAPI on Port 8095."""
    url = f"{PORTAL_API_BASE}/api/advocates/forge/status/{urllib.parse.quote(task_id)}"
    return _http_request(url, method="GET")


# ==============================================================================
# TMI & WEBSLINGER TELEMETRY INTERFACE (PORTS 8000 & 8095)
# ==============================================================================

def get_media_assets(advocate: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve registered media assets from cmdb_ci_media_asset."""
    url = f"{PORTAL_API_BASE}/api/media/assets"
    if advocate:
        url += f"?advocate={urllib.parse.quote(advocate)}"
    return _http_request(url, method="GET")

def register_media_asset(
    advocate: str,
    expression: str,
    file_path: str,
    sha256: str = "",
    category: str = "Canonical Anchor",
    mime_type: str = "image/jpeg",
    name: Optional[str] = None
) -> Dict[str, Any]:
    """Register a canonical media asset into cmdb_ci_media_asset and sys_media_asset via Portal API."""
    url = f"{PORTAL_API_BASE}/api/media/assets/register"
    payload = {
        "advocate": advocate,
        "expression": expression,
        "file_path": file_path,
        "sha256": sha256,
        "category": category,
        "mime_type": mime_type,
        "name": name or f"{advocate.capitalize()} ({expression})"
    }
    return _http_request(url, method="POST", data=payload)


def get_tmi_telemetry_rules() -> Dict[str, Any]:
    """Retrieve all active telemetry trigger rules from sys_tmi_telemetry_map."""
    url = f"{RELAY_API_BASE}/api/tmi_telemetry_map"
    return _http_request(url, method="GET")

def get_webslinger_events() -> Dict[str, Any]:
    """Retrieve all active webslinger templates from sys_webslinger_event."""
    url = f"{RELAY_API_BASE}/api/webslinger_events"
    return _http_request(url, method="GET")

# ==============================================================================
# "WHO'S ON FIRST?" SPATIAL DIAMOND STATE (PORT 8095)
# ==============================================================================

def get_diamond_state(game_id: str) -> Dict[str, Any]:
    """Retrieve real-time 1B, 2B, 3B base runner positions and counts for a game."""
    url = f"{PORTAL_API_BASE}/api/sports/diamond_state/{urllib.parse.quote(game_id)}"
    return _http_request(url, method="GET")

def send_diamond_event(game_id: str, event_type: str, batter: Optional[str] = None, 
                       pitcher: Optional[str] = None, balls: Optional[int] = None,
                       strikes: Optional[int] = None, outs: Optional[int] = None,
                       description: str = "") -> Dict[str, Any]:
    """Send live pitch or play event to advance the spatial diamond state machine."""
    url = f"{PORTAL_API_BASE}/api/sports/diamond_state/{urllib.parse.quote(game_id)}/event"
    payload = {
        "event_type": event_type,
        "batter_name": batter,
        "pitcher_name": pitcher,
        "balls": balls,
        "strikes": strikes,
        "outs": outs,
        "description": description
    }
    return _http_request(url, method="POST", data=payload)

def get_sports_telemetry_audit(game_pk: str, limit: int = 50) -> Dict[str, Any]:
    """Retrieve MLB ground-truth telemetry audit ledger entries for a game_pk via FastAPI Port 8095."""
    url = f"{PORTAL_API_BASE}/api/sports/telemetry/audit/{urllib.parse.quote(str(game_pk))}?limit={limit}"
    return _http_request(url, method="GET")

# ==============================================================================
# JIT APPROVAL QUEUE SDK (PORT 8095)
# ==============================================================================

def get_approvals(state: Optional[str] = None, auth_level: Optional[str] = None,
                  task_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve approvals from sys_approval_queue with optional state/auth filters."""
    params = {}
    if state:
        params["state"] = state
    if auth_level:
        params["auth_level"] = auth_level
    if task_id:
        params["task_id"] = task_id
    params["limit"] = limit
    
    query_str = urllib.parse.urlencode(params)
    url = f"{PORTAL_API_BASE}/api/approvals?{query_str}"
    data = _http_request(url, method="GET")
    return data.get("approvals", []) if isinstance(data, dict) else data

def create_approval(task_id: str, title: str, plan_markdown: str = "",
                    state: str = "Requested", auth_level: str = "omega=0",
                    assigned_to: str = "james", sys_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new approval request in sys_approval_queue via REST API."""
    url = f"{PORTAL_API_BASE}/api/approvals"
    payload = {
        "task_id": task_id,
        "title": title,
        "plan_markdown": plan_markdown,
        "state": state,
        "auth_level": auth_level,
        "assigned_to": assigned_to,
        "sys_id": sys_id
    }
    return _http_request(url, method="POST", data=payload)

def update_approval(appr_id: str, state: Optional[str] = None,
                    auth_level: Optional[str] = None,
                    plan_markdown: Optional[str] = None) -> Dict[str, Any]:
    """Update approval state (e.g. 'Executing', 'Executed', 'Pending Implementation') via REST."""
    url = f"{PORTAL_API_BASE}/api/approvals/{urllib.parse.quote(appr_id)}"
    payload = {}
    if state is not None:
        payload["state"] = state
    if auth_level is not None:
        payload["auth_level"] = auth_level
    if plan_markdown is not None:
        payload["plan_markdown"] = plan_markdown
    return _http_request(url, method="PUT", data=payload)

# ==============================================================================
# ENTERPRISE USER MANAGEMENT (PORT 8095) - CRUD SDK
# ==============================================================================

def list_users(role: Optional[str] = None, active: Optional[int] = None,
               search: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """List registered users via FastAPI REST endpoint with optional filters."""
    params = {"limit": limit, "offset": offset}
    if role is not None:
        params["role"] = role
    if active is not None:
        params["active"] = active
    if search is not None:
        params["search"] = search
    query_str = urllib.parse.urlencode(params)
    url = f"{PORTAL_API_BASE}/api/users?{query_str}"
    res = _http_request(url, method="GET")
    return res.get("users", []) if isinstance(res, dict) else []

def get_user(user_id_or_name: str) -> Dict[str, Any]:
    """Retrieve full user profile by sys_id or user_name."""
    url = f"{PORTAL_API_BASE}/api/users/{urllib.parse.quote(user_id_or_name)}"
    res = _http_request(url, method="GET")
    return res.get("user", {}) if isinstance(res, dict) else {}

def create_user(user_name: str, password: Optional[str] = None,
                display_name: Optional[str] = None, email: Optional[str] = None,
                role: str = "spectator", first_name: Optional[str] = None,
                last_name: Optional[str] = None, title: Optional[str] = None,
                introduction: Optional[str] = None, favorite_team: str = "NYM",
                city: Optional[str] = None, department: Optional[str] = None,
                avatar_url: Optional[str] = None, active: int = 1) -> Dict[str, Any]:
    """Provision a new user account with hashed password and initial role via REST."""
    url = f"{PORTAL_API_BASE}/api/users"
    payload = {
        "user_name": user_name,
        "password": password,
        "display_name": display_name,
        "email": email,
        "role": role,
        "first_name": first_name,
        "last_name": last_name,
        "title": title,
        "introduction": introduction,
        "favorite_team": favorite_team,
        "city": city,
        "department": department,
        "avatar_url": avatar_url,
        "active": active
    }
    return _http_request(url, method="POST", data=payload)

def update_user(user_id_or_name: str, **fields) -> Dict[str, Any]:
    """Update fields on an existing user account via REST."""
    url = f"{PORTAL_API_BASE}/api/users/{urllib.parse.quote(user_id_or_name)}"
    return _http_request(url, method="PUT", data=fields)

def disable_user(user_id_or_name: str) -> Dict[str, Any]:
    """Quickly disable/deactivate a user account."""
    url = f"{PORTAL_API_BASE}/api/users/{urllib.parse.quote(user_id_or_name)}/status"
    return _http_request(url, method="PATCH", data={"active": 0})

def enable_user(user_id_or_name: str) -> Dict[str, Any]:
    """Quickly enable/reactivate a user account."""
    url = f"{PORTAL_API_BASE}/api/users/{urllib.parse.quote(user_id_or_name)}/status"
    return _http_request(url, method="PATCH", data={"active": 1})

def delete_user(user_id_or_name: str) -> Dict[str, Any]:
    """Delete a user account from the system."""
    url = f"{PORTAL_API_BASE}/api/users/{urllib.parse.quote(user_id_or_name)}"
    return _http_request(url, method="DELETE")

# ==============================================================================
# FANSTACK GENERATIVE MEDIA & RECIPE ENGINE (PORT 8095)
# ==============================================================================

def get_media_recipes() -> Dict[str, Any]:
    """Retrieve available art style presets and baseball event prompt recipes."""
    url = f"{PORTAL_API_BASE}/api/media/recipes"
    return _http_request(url, method="GET")

def synthesize_media(event_type: str = "HOME_RUN", style_key: str = "PHOTOREAL_3D",
                     batter: str = "Pete Alonso", pitcher: str = "Zack Wheeler",
                     team: str = "NYM", opponent: str = "PHI",
                     venue: str = "Citi Field", custom_details: str = "",
                     duration_seconds: int = 6) -> Dict[str, Any]:
    """Synthesize video highlight via Google GenAI / FFmpeg faststart pipeline."""
    url = f"{PORTAL_API_BASE}/api/media/synthesize"
    payload = {
        "event_type": event_type,
        "style_key": style_key,
        "batter": batter,
        "pitcher": pitcher,
        "team": team,
        "opponent": opponent,
        "venue": venue,
        "custom_details": custom_details,
        "duration_seconds": duration_seconds
    }
    return _http_request(url, method="POST", data=payload)

def get_media_catalog() -> Dict[str, Any]:
    """Retrieve list of generated media assets from the FanStack vault."""
    url = f"{PORTAL_API_BASE}/api/media/catalog"
    return _http_request(url, method="GET")

# ==============================================================================
# MAM CHARACTER VISUAL ANCHORS & LOOKBOOKS (PORT 8095)
# ==============================================================================

def get_character_anchor(character: str) -> Dict[str, Any]:
    """Resolve single source of truth character anchor images and canonical styles from MAM."""
    url = f"{PORTAL_API_BASE}/api/mam/anchors/{urllib.parse.quote(character)}"
    return _http_request(url, method="GET")


# ==============================================================================
# AETHERVET CLINICAL SUITE CLIENT METHODS
# ==============================================================================

def get_aethervet_patients() -> List[Dict[str, Any]]:
    """List all registered patients in AetherVet clinical suite."""
    url = f"{PORTAL_API_BASE}/api/aethervet/patients"
    return _http_request(url, method="GET")


def ingress_aethervet_telemetry(
    zone_name: str,
    event_type: str,
    subject_ci: str = "metsy",
    dwell_duration_seconds: float = 0.0,
    bowl_fill_ratio: float = 1.0,
    snapshot_path: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> Dict[str, Any]:
    """Ingress an edge vision or GPS telemetry event to AetherVet clinical suite."""
    url = f"{PORTAL_API_BASE}/api/aethervet/telemetry/ingress"
    payload = {
        "subject_ci": subject_ci,
        "zone_name": zone_name,
        "event_type": event_type,
        "dwell_duration_seconds": dwell_duration_seconds,
        "bowl_fill_ratio": bowl_fill_ratio,
        "snapshot_path": snapshot_path,
        "lat": lat,
        "lon": lon
    }
    return _http_request(url, method="POST", data=payload)


def get_aethervet_status(subject_ci: str = "metsy") -> Dict[str, Any]:
    """Get active clinical state, last zone transition, and latest feeding event."""
    url = f"{PORTAL_API_BASE}/api/aethervet/status/{urllib.parse.quote(subject_ci)}"
    return _http_request(url, method="GET")


def get_aethervet_feeding_telemetry(subject_ci: str = "metsy", days: int = 30) -> Dict[str, Any]:
    """Get aggregated feeding duration curves and meal logs for clinical review."""
    url = f"{PORTAL_API_BASE}/api/aethervet/telemetry/feeding?subject_ci={urllib.parse.quote(subject_ci)}&days={days}"
    return _http_request(url, method="GET")


def generate_aethervet_dossier(
    subject_ci: str = "metsy",
    doctor_name: str = "Dr. Rox",
    date_range_days: int = 30,
    include_raw_telemetry: bool = True
) -> Dict[str, Any]:
    """Generate the pre-visit clinical dossier for Dr. Rox."""
    url = f"{PORTAL_API_BASE}/api/aethervet/dossier/generate"
    payload = {
        "subject_ci": subject_ci,
        "doctor_name": doctor_name,
        "date_range_days": date_range_days,
        "include_raw_telemetry": include_raw_telemetry
    }
    return _http_request(url, method="POST", data=payload)


def get_inference_mode() -> Dict[str, Any]:
    """Retrieve active FanStack advocate discourse inference mode."""
    url = f"{PORTAL_API_BASE}/api/fanstack/inference_mode"
    return _http_request(url, method="GET")


def set_inference_mode(mode: str) -> Dict[str, Any]:
    """Set active FanStack advocate discourse inference mode (CLOUD_API or LOCAL_CORPUS)."""
    url = f"{PORTAL_API_BASE}/api/fanstack/inference_mode"
    return _http_request(url, method="PUT", data={"mode": mode})


def get_chat_policy() -> Dict[str, Any]:
    """Retrieve active FanStack advocate chatter policy and room switches."""
    url = f"{PORTAL_API_BASE}/api/fanstack/chat_policy"
    return _http_request(url, method="GET")


def update_chat_policy(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update active FanStack advocate chatter policy and room switches."""
    url = f"{PORTAL_API_BASE}/api/fanstack/chat_policy"
    return _http_request(url, method="PUT", data=payload)


def get_hygiene_presets() -> Dict[str, Any]:
    """Retrieve canonical preset targets for Code Hygiene Sentinel audits."""
    url = f"{PORTAL_API_BASE}/api/hygiene/presets"
    return _http_request(url, method="GET")


def run_hygiene_audit(target: str = ".", fail_fast: bool = False) -> Dict[str, Any]:
    """Execute static Code Hygiene Sentinel audit on target path."""
    url = f"{PORTAL_API_BASE}/api/hygiene/audit"
    return _http_request(url, method="POST", data={"target": target, "fail_fast": fail_fast})


def export_hygiene_report(target: str = ".", markdown_content: Optional[str] = None) -> Dict[str, Any]:
    """Save an official Markdown audit report into sovereign_inbox/reports/."""
    url = f"{PORTAL_API_BASE}/api/hygiene/export"
    return _http_request(url, method="POST", data={"target": target, "markdown_content": markdown_content})


# ==============================================================================
# BROADCAST NETWORK & THE BLUNDERDOME (PORT 8095)
# ==============================================================================

def get_broadcast_shows() -> List[Dict[str, Any]]:
    """Retrieve all registered broadcast shows / radio stations."""
    url = f"{PORTAL_API_BASE}/api/broadcast/shows"
    return _http_request(url, method="GET")


def get_broadcast_episodes(show_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """List broadcast episodes with optional show filtering."""
    url = f"{PORTAL_API_BASE}/api/broadcast/episodes?limit={limit}"
    if show_id:
        url += f"&show_id={urllib.parse.quote(show_id)}"
    return _http_request(url, method="GET")


def get_broadcast_episode(episode_id: str) -> Dict[str, Any]:
    """Fetch complete episode detail along with timecoded dialogue segments."""
    url = f"{PORTAL_API_BASE}/api/broadcast/episodes/{urllib.parse.quote(episode_id)}"
    return _http_request(url, method="GET")


def get_dsp_presets() -> List[Dict[str, Any]]:
    """List available environmental DSP presets."""
    url = f"{PORTAL_API_BASE}/api/broadcast/presets/dsp"
    return _http_request(url, method="GET")


def generate_broadcast_episode(
    title: str,
    topic: str,
    seat_roster: List[Dict[str, Any]],
    show_id: str = "show_blunderdome",
    trigger_context: str = "",
    game_pk: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an autonomous talk radio episode via MARD broadcast engine.
    Zero-hardcoding: seats are passed dynamically.
    """
    url = f"{PORTAL_API_BASE}/api/broadcast/generate"
    payload = {
        "show_id": show_id,
        "title": title,
        "topic": topic,
        "seat_roster": seat_roster,
        "trigger_context": trigger_context,
        "game_pk": game_pk
    }
    return _http_request(url, method="POST", data=payload)


# ==============================================================================
# MID-SESSION PROGRESS REPORTS (PORT 8095)
# ==============================================================================

def get_progress_reports() -> List[Dict[str, Any]]:
    """Retrieve all mid-session progress reports."""
    url = f"{PORTAL_API_BASE}/api/progress/reports"
    res = _http_request(url, method="GET")
    return res.get("reports", []) if isinstance(res, dict) else []


def trigger_progress_report(
    session_title: str = "Active Sovereign Sprint", 
    in_flight: str = "", 
    decisions_needed: str = "None currently. Sprint is on track.",
    trigger_sync: bool = False
) -> Dict[str, Any]:
    """Trigger generation of a mid-session progress report via FastAPI."""
    url = f"{PORTAL_API_BASE}/api/progress/generate"
    payload = {
        "session_title": session_title,
        "in_flight": in_flight,
        "decisions_needed": decisions_needed,
        "trigger_sync": trigger_sync
    }
    return _http_request(url, method="POST", data=payload)


# ==============================================================================
# SOVEREIGN SENTINEL RANCH & HERD TELEMETRY (PORT 8095)
# ==============================================================================

def get_sentinel_overview() -> Dict[str, Any]:
    """Retrieve Sovereign Sentinel high-level herd health and infrastructure status."""
    url = f"{PORTAL_API_BASE}/api/sentinel/overview"
    return _http_request(url, method="GET")

def get_sentinel_animals() -> List[Dict[str, Any]]:
    """Retrieve all 25 registered Texas Longhorns with latest telemetry."""
    url = f"{PORTAL_API_BASE}/api/sentinel/animals"
    res = _http_request(url, method="GET")
    return res.get("animals", []) if isinstance(res, dict) else []

def get_sentinel_animal_detail(animal_id: str) -> Dict[str, Any]:
    """Fetch individual animal profile and 14-day rumination curve."""
    url = f"{PORTAL_API_BASE}/api/sentinel/animals/{urllib.parse.quote(animal_id)}"
    return _http_request(url, method="GET")

def get_sentinel_geofences() -> List[Dict[str, Any]]:
    """Retrieve Sector 4 geofenced pasture zones."""
    url = f"{PORTAL_API_BASE}/api/sentinel/geofences"
    res = _http_request(url, method="GET")
    return res.get("geofences", []) if isinstance(res, dict) else []

def trigger_sentinel_scenario(scenario_id: int) -> Dict[str, Any]:
    """Trigger one of 4 deterministic herd scenarios (1: Grazing, 2: Dystocia, 3: Tank Dry, 4: BRD)."""
    url = f"{PORTAL_API_BASE}/api/sentinel/scenario/{scenario_id}"
    return _http_request(url, method="POST")

def post_sentinel_voice_heal(utterance: str, operator: str = "james") -> Dict[str, Any]:
    """Execute rugged voice triage with instant sub-second INC ticket hydration."""
    url = f"{PORTAL_API_BASE}/api/sentinel/voice_heal"
    return _http_request(url, method="POST", data={"utterance": utterance, "operator": operator})

def get_sentinel_voice_incidents() -> List[Dict[str, Any]]:
    """Retrieve recent voice heal logs."""
    url = f"{PORTAL_API_BASE}/api/sentinel/voice_incidents"
    res = _http_request(url, method="GET")
    return res.get("incidents", []) if isinstance(res, dict) else []

def get_sentinel_mard_stream() -> Dict[str, Any]:
    """Retrieve the active 4-agent dialectic consensus stream."""
    url = f"{PORTAL_API_BASE}/api/sentinel/mard_stream"
    return _http_request(url, method="GET")


# ==============================================================================
# SOVEREIGN NEURAL FLYWHEEL INFERENCE CLIENT (COLAB / PEGASUS / EDGE)
# ==============================================================================

def query_neural_flywheel_inference(
    messages: List[Dict[str, str]], 
    inference_url: Optional[str] = None,
    max_tokens: int = 512,
    temperature: float = 0.7,
    timeout: float = 60.0
) -> Dict[str, Any]:
    """
    Query the fine-tuned Sovereign Neural Flywheel (Qwen 2.5 / BrandForge / CodeSentinel)
    running on Colab A100 tunnel or edge node.
    """
    base_url = inference_url or os.getenv("SOVEREIGN_INFERENCE_URL", "http://127.0.0.1:8000/v1")
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    return _http_request(url, method="POST", data=payload, timeout=timeout)


# ==============================================================================
# SPORTS PRE-GAME INTELLIGENCE DOSSIER (WO-2026-0908)
# ==============================================================================

def get_pregame_intel(game_pk: str) -> Dict[str, Any]:
    """Fetch pre-game scouting intelligence dossier for a game."""
    url = f"{CORE_API_BASE}/api/sports/pregame-intel/{urllib.parse.quote(str(game_pk))}"
    try:
        return _http_request(url, method="GET")
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/pregame-intel/{urllib.parse.quote(str(game_pk))}"
        return _http_request(fallback_url, method="GET")

def get_active_pregame_intel() -> Dict[str, Any]:
    """Fetch pre-game intelligence for the currently active or imminent game."""
    url = f"{CORE_API_BASE}/api/sports/pregame-intel/active"
    try:
        return _http_request(url, method="GET")
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/pregame-intel/active"
        return _http_request(fallback_url, method="GET")

def upsert_pregame_intel(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert pre-game intelligence dossier via API."""
    url = f"{CORE_API_BASE}/api/sports/pregame-intel"
    try:
        return _http_request(url, method="POST", data=payload)
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/pregame-intel"
        return _http_request(fallback_url, method="POST", data=payload)

# ==============================================================================
# PIZZA-BOT & HEDLIF FLEET EQUITY ENGINE (PORT 8095)
# ==============================================================================

def get_pizzabot_health() -> Dict[str, Any]:
    """Check Pizza-Bot and HEDLIF Equity Engine operational health."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/health"
    return _http_request(url, method="GET")

def get_pizza_orders(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve pizza orders from sovereign_now.db with optional status filter."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/orders"
    if status:
        url += f"?status={urllib.parse.quote(status)}"
    res = _http_request(url, method="GET")
    return res.get("orders", []) if isinstance(res, dict) else []

def get_pizza_order_detail(order_id: str) -> Dict[str, Any]:
    """Retrieve full order details including line items and Knot hashes."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/orders/{urllib.parse.quote(order_id)}"
    return _http_request(url, method="GET")

def create_pizza_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Stage a new Pizza Order into sovereign_now.db."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/orders"
    return _http_request(url, method="POST", data=payload)

def update_pizza_order_status(order_id: str, status: str, driver_id: Optional[str] = None, bypass_knot: bool = False) -> Dict[str, Any]:
    """Update order status with Sovereign Knot Proof-of-Bake/Handoff validation."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/orders/{urllib.parse.quote(order_id)}/status"
    payload = {
        "status": status,
        "assigned_driver_id": driver_id,
        "bypass_knot_proof": bypass_knot
    }
    return _http_request(url, method="PUT", data=payload)

def get_hedlif_drivers() -> List[Dict[str, Any]]:
    """Retrieve all fleet delivery drivers with cumulative tips and ethical resistance."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/drivers"
    res = _http_request(url, method="GET")
    return res.get("drivers", []) if isinstance(res, dict) else []

def register_hedlif_driver(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Register or update a fleet delivery driver."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/drivers"
    return _http_request(url, method="POST", data=payload)

def evaluate_hedlif_dispatch(beta_dampening: float = 5.0) -> Dict[str, Any]:
    """Execute HEDLIF dispatch evaluation algorithm across active fleet and queued orders."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/dispatch/evaluate"
    return _http_request(url, method="POST", data={"beta_dampening": beta_dampening})

def get_pizzabot_kds_status() -> Dict[str, Any]:
    """Retrieve Kitchen Display System (KDS), thermal decks, and fleet status."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/kds/status"
    return _http_request(url, method="GET")

def send_driver_telemetry_ping(driver_handle: str, lat: float, lng: float, speed_mph: float = 0.0, heading: float = 0.0, battery_pct: int = 100) -> Dict[str, Any]:
    """Send live GPS telemetry ping from driver phone (PWA or OwnTracks)."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/telemetry/ping"
    payload = {
        "driver_handle": driver_handle,
        "lat": lat,
        "lng": lng,
        "speed_mph": speed_mph,
        "heading": heading,
        "battery_pct": battery_pct
    }
    return _http_request(url, method="POST", data=payload)

def confirm_order_delivery(order_id: str, driver_handle: str, lat: float, lng: float, bypass_geofence: bool = False) -> Dict[str, Any]:
    """Confirm order drop with Sovereign Knot 50m geofence verification."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/orders/{urllib.parse.quote(order_id)}/deliver"
    payload = {
        "driver_handle": driver_handle,
        "driver_lat": lat,
        "driver_lng": lng,
        "bypass_geofence": bypass_geofence
    }
    return _http_request(url, method="POST", data=payload)

def get_fleet_telemetry() -> Dict[str, Any]:
    """Retrieve live fleet vector radar telemetry with positions and distance to active drop."""
    url = f"{PORTAL_API_BASE}/api/pizzabot/telemetry/fleet"
    return _http_request(url, method="GET")

# ==============================================================================
# FANCAST NFL DEAD-AIR BANTER ENGINE (PORT 8095) - WO0010035
# ==============================================================================

def get_fancast_banter_state() -> Dict[str, Any]:
    """Retrieve current FanCast banter mode, stoppage state, and recent banter cards."""
    url = f"{PORTAL_API_BASE}/api/fancast/banter/state"
    return _http_request(url, method="GET")

def set_fancast_banter_mode(mode: str) -> Dict[str, Any]:
    """Update active mode ('broadcast_safe' or 'emergent_chaos')."""
    url = f"{PORTAL_API_BASE}/api/fancast/banter/mode"
    return _http_request(url, method="POST", data={"mode": mode})

def trigger_fancast_banter(stoppage_type: str = "HUDDLE_40S", context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Ingest optical or telemetry stoppage trigger and generate banter turns."""
    url = f"{PORTAL_API_BASE}/api/fancast/banter/trigger"
    payload = {"stoppage_type": stoppage_type, "context": context or {}}
    return _http_request(url, method="POST", data=payload)

def interrupt_fancast_banter() -> Dict[str, Any]:
    """Snap detected or play clock < 5s; immediately halts active banter."""
    url = f"{PORTAL_API_BASE}/api/fancast/banter/interrupt"
    return _http_request(url, method="POST")

def get_fancast_banter_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch banter dialogue history."""
    url = f"{PORTAL_API_BASE}/api/fancast/banter/history?limit={limit}"
    return _http_request(url, method="GET")


# ==============================================================================
# AUDIENCE PULSE & REAL-TIME POLLING ENGINE (WO0010054)
# ==============================================================================

def create_poll(room_id: str, question: str, options: List[str], poll_type: str = "single", poll_id: Optional[str] = None) -> Dict[str, Any]:
    """Stage a new audience poll."""
    url = f"{CORE_API_BASE}/api/sports/polls/create"
    payload = {
        "poll_id": poll_id,
        "room_id": room_id,
        "question": question,
        "options": options,
        "poll_type": poll_type
    }
    try:
        return _http_request(url, method="POST", data=payload)
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/polls/create"
        return _http_request(fallback_url, method="POST", data=payload)

def publish_poll(poll_id: str) -> Dict[str, Any]:
    """Publish and activate an audience poll."""
    url = f"{CORE_API_BASE}/api/sports/polls/{urllib.parse.quote(poll_id)}/publish"
    try:
        return _http_request(url, method="POST")
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/polls/{urllib.parse.quote(poll_id)}/publish"
        return _http_request(fallback_url, method="POST")

def vote_poll(poll_id: str, voter_id: str, selected_option: int, room_id: str = "GLOBAL") -> Dict[str, Any]:
    """Cast an idempotent vote in an active poll."""
    url = f"{CORE_API_BASE}/api/sports/polls/{urllib.parse.quote(poll_id)}/vote"
    payload = {
        "room_id": room_id,
        "voter_id": voter_id,
        "selected_option": selected_option
    }
    try:
        return _http_request(url, method="POST", data=payload)
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/polls/{urllib.parse.quote(poll_id)}/vote"
        return _http_request(fallback_url, method="POST", data=payload)

def get_active_poll(room_id: str, voter_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve active poll and live tallies for a room."""
    q = f"?voter_id={urllib.parse.quote(voter_id)}" if voter_id else ""
    url = f"{CORE_API_BASE}/api/sports/polls/room/{urllib.parse.quote(room_id)}/active{q}"
    try:
        return _http_request(url, method="GET")
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/polls/room/{urllib.parse.quote(room_id)}/active{q}"
        return _http_request(fallback_url, method="GET")

def freeze_poll(poll_id: str) -> Dict[str, Any]:
    """Freeze voting on a poll (read-only state)."""
    url = f"{CORE_API_BASE}/api/sports/polls/{urllib.parse.quote(poll_id)}/freeze"
    try:
        return _http_request(url, method="POST")
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/polls/{urllib.parse.quote(poll_id)}/freeze"
        return _http_request(fallback_url, method="POST")

def close_poll(poll_id: str) -> Dict[str, Any]:
    """Close and archive a poll."""
    url = f"{CORE_API_BASE}/api/sports/polls/{urllib.parse.quote(poll_id)}/close"
    try:
        return _http_request(url, method="POST")
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/polls/{urllib.parse.quote(poll_id)}/close"
        return _http_request(fallback_url, method="POST")

def broadcast_poll(poll_id: str) -> Dict[str, Any]:
    """Push poll results to Broadcast TV HUD overlay."""
    url = f"{CORE_API_BASE}/api/sports/polls/{urllib.parse.quote(poll_id)}/broadcast"
    try:
        return _http_request(url, method="POST")
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/polls/{urllib.parse.quote(poll_id)}/broadcast"
        return _http_request(fallback_url, method="POST")

def list_polls(room_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List polls with tallies."""
    q = f"?room_id={urllib.parse.quote(room_id)}" if room_id else ""
    url = f"{CORE_API_BASE}/api/sports/polls/list{q}"
    try:
        return _http_request(url, method="GET")
    except Exception:
        fallback_url = f"{PORTAL_API_BASE}/api/sports/polls/list{q}"
        return _http_request(fallback_url, method="GET")

def create_in_game_poll(room_id: str, question: str, options: List[str], poll_type: str = "single", poll_id: Optional[str] = None) -> Dict[str, Any]:
    """Alias for create_poll."""
    return create_poll(room_id=room_id, question=question, options=options, poll_type=poll_type, poll_id=poll_id)

def vote_in_poll(poll_id: str, option_id: int, user_name: str, room_id: str = "GLOBAL") -> Dict[str, Any]:
    """Alias for vote_poll."""
    return vote_poll(poll_id=poll_id, voter_id=user_name, selected_option=option_id, room_id=room_id)

def get_room_polls(room_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Alias for list_polls."""
    return list_polls(room_id=room_id)

def trigger_govee_hardware(preset: str = "VICTORY_SWEEP", event_type: Optional[str] = None) -> Dict[str, Any]:
    """Trigger Govee LAN UDP multi-node smart lighting strobe on Port 4003."""
    url = f"{RELAY_API_BASE}/api/govee/trigger"
    payload = {"preset": preset, "event_type": event_type or preset}
    try:
        return _http_request(url, method="POST", data=payload)
    except Exception:
        fallback_url = "http://127.0.0.1:8008/api/govee/trigger"
        try:
            return _http_request(fallback_url, method="POST", data=payload)
        except Exception:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = json.dumps({"msg": {"cmd": "colorwc", "data": {"color": {"r": 0, "g": 255, "b": 128}}}}).encode('utf-8')
            for ip in ["192.168.1.173", "192.168.1.174", "192.168.1.176", "192.168.1.188"]:
                try:
                    sock.sendto(msg, (ip, 4003))
                except Exception:
                    pass
            sock.close()
            return {"status": "success", "preset": preset, "direct_udp_fallback": True}

trigger_govee_strobe = trigger_govee_hardware


# ==============================================================================
# SPORTS SCHEDULE & ROOM PERSONA ORCHESTRATION (PORT 8095)
# ==============================================================================

def seed_sport_schedule(
    game_pk: str,
    sport: str = "MLB",
    home_team: str = "NYM",
    away_team: str = "NYY",
    home_team_name: str = "New York Mets",
    away_team_name: str = "New York Yankees",
    game_date: str = "2026-05-17",
    game_time: str = "1:40 PM",
    venue: str = "Citi Field",
    status: str = "In Progress",
    room_state: str = "active",
    boggs_level: int = 3,
    home_score: int = 0,
    away_score: int = 0,
    postgame_raid_url: Optional[str] = None
) -> Dict[str, Any]:
    """Seed or upsert a game into sport_schedule via FastAPI on Port 8095."""
    url = f"{PORTAL_API_BASE}/api/sports/schedule/seed"
    payload = {
        "game_pk": str(game_pk),
        "sport": sport,
        "home_team": home_team,
        "away_team": away_team,
        "home_team_name": home_team_name,
        "away_team_name": away_team_name,
        "game_date": game_date,
        "game_time": game_time,
        "venue": venue,
        "status": status,
        "room_state": room_state,
        "boggs_level": boggs_level,
        "home_score": home_score,
        "away_score": away_score
    }
    if postgame_raid_url:
        payload["postgame_raid_url"] = postgame_raid_url
    return _http_request(url, method="POST", data=payload)

def update_fanstack_room(game_pk_or_id: str, **kwargs) -> Dict[str, Any]:
    """Update fanstack room record in cmdb_ci_fanstack_room via FastAPI on Port 8095."""
    url = f"{PORTAL_API_BASE}/api/now/table/cmdb_ci_fanstack_room/{urllib.parse.quote(str(game_pk_or_id))}"
    return _http_request(url, method="PUT", data=kwargs)

def get_fanstack_rooms() -> List[Dict[str, Any]]:
    """Retrieve all fanstack room records via FastAPI on Port 8095."""
    url = f"{PORTAL_API_BASE}/api/now/table/cmdb_ci_fanstack_room"
    data = _http_request(url, method="GET")
    return data.get("result", []) if isinstance(data, dict) else []

def seat_room_personas(
    game_pk: str,
    personas: List[str],
    prompt_overlay: Optional[str] = None,
    clear_existing: bool = True
) -> Dict[str, Any]:
    """Seat fan personas into a game room via FastAPI on Port 8095."""
    url = f"{PORTAL_API_BASE}/api/sports/rooms/{urllib.parse.quote(str(game_pk))}/personas"
    payload = {
        "personas": personas,
        "prompt_overlay": prompt_overlay,
        "clear_existing": clear_existing
    }
    return _http_request(url, method="POST", data=payload)

def get_room_personas(game_pk: str) -> Dict[str, Any]:
    """Retrieve all personas currently seated in a game room."""
    url = f"{PORTAL_API_BASE}/api/sports/rooms/{urllib.parse.quote(str(game_pk))}/personas"
    return _http_request(url, method="GET")

def remove_room_persona(game_pk: str, persona: str) -> Dict[str, Any]:
    """Remove a persona from a game room via FastAPI on Port 8095 (WO0010160)."""
    url = f"{PORTAL_API_BASE}/api/sports/rooms/{urllib.parse.quote(str(game_pk))}/personas/{urllib.parse.quote(str(persona))}"
    return _http_request(url, method="DELETE")

def bring_gang(
    target_room_id: str,
    source_room_id: Optional[str] = None,
    personas: Optional[List[str]] = None,
    prompt_overlay: Optional[str] = None
) -> Dict[str, Any]:
    """Execute Bring Gang entourage transfer protocol via FastAPI (WO0010160)."""
    url = f"{PORTAL_API_BASE}/api/fanstack/bring_gang"
    payload = {
        "target_room_id": target_room_id,
        "source_room_id": source_room_id,
        "personas": personas,
        "prompt_overlay": prompt_overlay
    }
    return _http_request(url, method="POST", data=payload)

def get_nfl_live_state(game_pk: str, mode: str = "live", play: Optional[int] = None) -> Dict[str, Any]:
    """Fetch live authentic NFL telemetry or video-synced replay drive from FastAPI."""
    params = f"?mode={mode}"
    if play is not None:
        params += f"&play={play}"
    url = f"{PORTAL_API_BASE}/api/nfl/live/{urllib.parse.quote(str(game_pk))}{params}"
    return _http_request(url, method="GET")

def get_classic_game_state(game_pk: str, play: Optional[int] = 1) -> Dict[str, Any]:
    """Fetch synchronized historical game replay telemetry and authentic persona lore from FastAPI."""
    params = f"?play={play}" if play is not None else ""
    url = f"{PORTAL_API_BASE}/api/sports/classic/{urllib.parse.quote(str(game_pk))}{params}"
    return _http_request(url, method="GET")

def deploy_football_room(game_pk: str, team_away: Optional[str] = None, team_home: Optional[str] = None, away_team: Optional[str] = None, home_team: Optional[str] = None, sport: Optional[str] = None) -> Dict[str, Any]:
    """On-demand deploy football watch room and seat authentic team advocates via FastAPI (WO0010093 / WO0010094)."""
    url = f"{PORTAL_API_BASE}/api/sports/football/deploy_room"
    eff_away = away_team or team_away or "TENN"
    eff_home = home_team or team_home or "GT"
    payload = {
        "game_pk": str(game_pk),
        "away_team": eff_away,
        "home_team": eff_home,
        "team_away": eff_away,
        "team_home": eff_home,
        "sport": sport or "cfb"
    }
    return _http_request(url, method="POST", data=payload)

def get_football_room_status(game_pk: str) -> Dict[str, Any]:
    """Retrieve on-demand football watch room status and seated advocates via FastAPI (WO0010093)."""
    url = f"{PORTAL_API_BASE}/api/sports/football/room_status/{urllib.parse.quote(str(game_pk))}"
    return _http_request(url, method="GET")

def get_football_chat(game_pk: str) -> List[Dict[str, Any]]:
    """Retrieve chat message history for a football game watch room via FastAPI (WO0010095)."""
    url = f"{PORTAL_API_BASE}/api/sports/football/chat/{urllib.parse.quote(str(game_pk))}"
    return _http_request(url, method="GET")

def post_football_chat(game_pk: str, text: str, persona: str = "@pilot", msg_type: str = "user") -> Dict[str, Any]:
    """Post a chat message to a football game watch room via FastAPI (WO0010095)."""
    url = f"{PORTAL_API_BASE}/api/sports/football/chat/{urllib.parse.quote(str(game_pk))}"
    payload = {
        "persona": persona,
        "text": text,
        "msg_type": msg_type
    }
    return _http_request(url, method="POST", data=payload)


# ==============================================================================
# FANCAST JETEXTRACTORS LIVE SPORTS STREAM RESOLVER (WO0010067)
# ==============================================================================

def resolve_sports_stream(league: str, team_or_game: str) -> Dict[str, Any]:
    """Auto-resolve live sports stream (.m3u8 manifest and headers) via FastAPI."""
    url = f"{PORTAL_API_BASE}/api/stream/resolve/{urllib.parse.quote(league)}/{urllib.parse.quote(team_or_game)}"
    return _http_request(url, method="GET")

def get_sports_stream_sources(league: Optional[str] = None) -> Dict[str, Any]:
    """Get sports stream extraction sources via FastAPI."""
    endpoint = f"/api/stream/sources/{urllib.parse.quote(league)}" if league else "/api/stream/sources"
    url = f"{PORTAL_API_BASE}{endpoint}"
    return _http_request(url, method="GET")


# ==============================================================================
# STATCAST SAVANT ORACLE & JAKE TAYLOR UMPIRE NODE (WO0010070)
# ==============================================================================

def query_savant_oracle(query: str) -> Dict[str, Any]:
    """Execute natural language Text-to-SQL over 807MB statcast_pitches database via FastAPI."""
    url = f"{PORTAL_API_BASE}/api/savant_query"
    return _http_request(url, method="POST", data={"query": query})


def arbitrate_umpire_rule(query: str, current_pitch: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Arbitrate controversial MLB plays and strike zone audits via Jake Taylor Umpire Node."""
    url = f"{PORTAL_API_BASE}/api/umpire/arbitrate"
    return _http_request(url, method="POST", data={"query": query, "current_pitch": current_pitch})


# ==============================================================================
# WEEDSTACK MEAN GENE GUERILLA DISCOURSE (WO0010071)
# ==============================================================================

def trigger_weedstack_discourse(room: str = "823498", delay_override: Optional[float] = 0.1) -> Dict[str, Any]:
    """Trigger the 4-step wrestling heel-and-face guerilla discourse loop via FastAPI."""
    url = f"{PORTAL_API_BASE}/api/discourse/trigger_weedstack_loop"
    return _http_request(url, method="POST", data={"room": room, "delay_override": delay_override})


def deploy_persona(
    handle: str,
    display_name: str,
    team: str = "GLOBAL",
    system_prompt: str = "",
    deep_lore: str = "",
    behavior_notes: str = "",
    governance: str = "",
    color: str = "#00b4d8",
    cadence: str = "pacer",
    boggs_level: int = 2,
    avatar_url: str = "",
    rooms: Optional[List[str]] = None,
    canned_takes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Deploy and seat a persona transactionally across persona, cmdb_ci, and m2m_persona_room via FastAPI."""
    url = f"{PORTAL_API_BASE}/api/system/forge/deploy"
    payload = {
        "handle": handle,
        "display_name": display_name,
        "team": team,
        "system_prompt": system_prompt,
        "deep_lore": deep_lore,
        "behavior_notes": behavior_notes,
        "governance": governance,
        "color": color,
        "cadence": cadence,
        "boggs_level": boggs_level,
        "avatar_url": avatar_url,
        "rooms": rooms or [],
        "canned_takes": canned_takes or []
    }
    return _http_request(url, method="POST", data=payload)


def purge_room_chat(game_pk: str) -> Dict[str, Any]:
    """Purge chat messages for a specific game room across database and memory buffers via FastAPI."""
    url = f"{PORTAL_API_BASE}/api/chat/rooms/{urllib.parse.quote(str(game_pk))}/purge"
    try:
        return _http_request(url, method="POST", data={})
    except Exception:
        fallback_url = f"http://127.0.0.1:8000/api/chat/rooms/{urllib.parse.quote(str(game_pk))}/purge"
        return _http_request(fallback_url, method="POST", data={})


def get_chat_history(game_pk: str) -> Dict[str, Any]:
    """Fetch chat history for a specific game room via FanStack / SDLC API."""
    url = f"http://127.0.0.1:8000/api/game-log/chat/{urllib.parse.quote(str(game_pk))}"
    return _http_request(url, method="GET")


# ── SOVEREIGN ANTI-SURVEILLANCE PRICE SHIELD SDK (WO0010080) ───────────────

def audit_surveillance_price(url: str, requested_by: str = "pilot", profiles: Optional[List[str]] = None) -> Dict[str, Any]:
    """Audit a target retail/travel URL across multi-vantage browser profiles via FastAPI."""
    api_url = f"{PORTAL_API_BASE}/api/shield/audit_price"
    payload = {
        "url": url,
        "requested_by": requested_by,
        "profiles": profiles
    }
    return _http_request(api_url, method="POST", data=payload)


def get_price_shield_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch historical surveillance price discrimination audits from the database via FastAPI."""
    api_url = f"{PORTAL_API_BASE}/api/shield/audits?limit={limit}"
    return _http_request(api_url, method="GET")


def get_price_shield_status() -> Dict[str, Any]:
    """Fetch status of the Sovereign Price Shield engine and Pegasus edge sentries via FastAPI."""
    api_url = f"{PORTAL_API_BASE}/api/shield/status"
    return _http_request(api_url, method="GET")


def generate_adversarial_noise(category: str = "retail") -> Dict[str, Any]:
    """Dispatch synthetic adversarial browsing queries to dilute data broker graphs via FastAPI."""
    api_url = f"{PORTAL_API_BASE}/api/shield/generate_noise"
    return _http_request(api_url, method="POST", data={"category": category})


# ── MARD AGENTIC CODING ASSEMBLY LINE SDK (WO0010081) ───────────────────────

def assembly_health() -> Dict[str, Any]:
    """Check MARD Assembly Line operational health and station capabilities manifest."""
    api_url = f"{PORTAL_API_BASE}/api/assembly/health"
    return _http_request(api_url, method="GET")


def dispatch_assembly_run(
    ticket_id: str,
    brief: str,
    assigned_model: str = "gemini-3.5-flash",
    max_retries: int = 3,
    execution_node: str = "clio",
    auto_run: bool = False
) -> Dict[str, Any]:
    """Initialize and dispatch a new 5-station agentic coding assembly line run."""
    api_url = f"{PORTAL_API_BASE}/api/assembly/dispatch"
    payload = {
        "ticket_id": ticket_id,
        "brief": brief,
        "assigned_model": assigned_model,
        "max_retries": max_retries,
        "execution_node": execution_node,
        "auto_run": auto_run
    }
    return _http_request(api_url, method="POST", data=payload)


def list_assembly_runs(limit: int = 50, state: Optional[str] = None) -> List[Dict[str, Any]]:
    """List recent agentic coding assembly line runs."""
    params = f"?limit={limit}"
    if state:
        params += f"&state={urllib.parse.quote(state)}"
    api_url = f"{PORTAL_API_BASE}/api/assembly/runs{params}"
    return _http_request(api_url, method="GET")


def get_assembly_run(run_id: str) -> Dict[str, Any]:
    """Fetch complete telemetry, current state, and immutable artifacts for an assembly run."""
    api_url = f"{PORTAL_API_BASE}/api/assembly/runs/{urllib.parse.quote(run_id)}"
    return _http_request(api_url, method="GET")


def step_assembly_run(run_id: str) -> Dict[str, Any]:
    """Advance the assembly run to the next station in the 5-station pipeline."""
    api_url = f"{PORTAL_API_BASE}/api/assembly/runs/{urllib.parse.quote(run_id)}/step"
    return _http_request(api_url, method="POST", data={}, timeout=120.0)


def run_assembly_pipeline(run_id: str) -> Dict[str, Any]:
    """Execute all stations sequentially until terminal state (COMPLETED or CIRCUIT_TRIPPED)."""
    api_url = f"{PORTAL_API_BASE}/api/assembly/runs/{urllib.parse.quote(run_id)}/run"
    return _http_request(api_url, method="POST", data={}, timeout=300.0)


def reset_assembly_circuit(run_id: str, new_brief: Optional[str] = None) -> Dict[str, Any]:
    """Reset a tripped circuit breaker to allow fresh attempts with optional refined brief."""
    api_url = f"{PORTAL_API_BASE}/api/assembly/runs/{urllib.parse.quote(run_id)}/reset"
    payload = {"new_brief": new_brief} if new_brief else {}
    return _http_request(api_url, method="POST", data=payload)


def get_assembly_artifacts(
    run_id: str,
    station_id: Optional[int] = None,
    artifact_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve immutable artifact breadcrumbs for an assembly run."""
    params = []
    if station_id:
        params.append(f"station_id={station_id}")
    if artifact_type:
        params.append(f"artifact_type={urllib.parse.quote(artifact_type)}")
    query = f"?{'&'.join(params)}" if params else ""
    api_url = f"{PORTAL_API_BASE}/api/assembly/runs/{urllib.parse.quote(run_id)}/artifacts{query}"
    return _http_request(api_url, method="GET")


def get_next_ticket_number(
    category: str = "WO",
    slug: Optional[str] = None,
    increment: bool = False
) -> Dict[str, Any]:
    """
    Query the next sequential auto-number and optional hybrid ID via FastAPI REST API.
    Complies with Invariant I.8 & I.9 (Campsite Protocol & FastAPI-First SDK).
    """
    params = [f"category={urllib.parse.quote(category)}"]
    if slug:
        params.append(f"slug={urllib.parse.quote(slug)}")
    if increment:
        params.append("increment=true")
    query = f"?{'&'.join(params)}"
    url = f"{PORTAL_API_BASE}/api/tickets/next_number{query}"
    return _http_request(url, method="GET")


# -------------------------------------------------------------
# IN-BREAK ENTERTAINMENT SUITE & ZORK SERVICE CLIENT HELPERS
# -------------------------------------------------------------

def get_infill_playlist(sport: str = "MLB", break_type: str = "COMMERCIAL") -> Dict[str, Any]:
    """Retrieve adaptive infill media items (parody ads, advocate takes, tributes)."""
    url = f"{PORTAL_API_BASE}/api/fanstack/infill_playlist?sport={urllib.parse.quote(sport)}&break_type={urllib.parse.quote(break_type)}"
    return _http_request(url, method="GET")


def get_fanstack_trivia(sport: str = "MLB", matchup: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve rapid matchup trivia questions."""
    q = f"?sport={urllib.parse.quote(sport)}"
    if matchup:
        q += f"&matchup={urllib.parse.quote(matchup)}"
    url = f"{PORTAL_API_BASE}/api/fanstack/trivia{q}"
    return _http_request(url, method="GET")


def execute_zork_command(user_id: str, match_id: str = "823584", command: str = "LOOK") -> Dict[str, Any]:
    """Execute natural language text adventure command in Shea Stadium Sub-Level 3."""
    url = f"{PORTAL_API_BASE}/api/fanstack/zork/command"
    payload = {"user_id": user_id, "match_id": match_id, "command": command}
    return _http_request(url, method="POST", data=payload)


def get_zork_session(user_id: str, match_id: str = "823584") -> Dict[str, Any]:
    """Fetch current Zork terminal state and room coordinates."""
    url = f"{PORTAL_API_BASE}/api/fanstack/zork/session/{urllib.parse.quote(user_id)}/{urllib.parse.quote(match_id)}"
    return _http_request(url, method="GET")


# -------------------------------------------------------------
# POST-GAME RECONCILIATION & TELEMETRY CLIENT (ENHC2026082608)
# -------------------------------------------------------------

def reconcile_game_telemetry(game_pk: int) -> Dict[str, Any]:
    """Trigger on-demand post-game telemetry reconciliation for a specific MLB game."""
    url = f"{PORTAL_API_BASE}/api/sports/telemetry/reconcile/{game_pk}"
    return _http_request(url, method="POST")


def get_game_reconciliations(limit: int = 50) -> Dict[str, Any]:
    """Retrieve historical post-game reconciliation records from the ledger."""
    url = f"{PORTAL_API_BASE}/api/sports/telemetry/reconciliations?limit={limit}"
    return _http_request(url, method="GET")


def get_game_reconciliation(game_pk: int) -> Dict[str, Any]:
    """Retrieve specific reconciliation details for a given game_pk."""
    url = f"{PORTAL_API_BASE}/api/sports/telemetry/reconciliations/{game_pk}"
    return _http_request(url, method="GET")


# -------------------------------------------------------------
# POLLER HEARTBEAT & SYSTEM STATUS CLIENT (WO0010108)
# -------------------------------------------------------------

def get_poller_status() -> Dict[str, Any]:
    """Retrieve live heartbeat telemetry and process health for Sovereign background pollers."""
    url = f"{PORTAL_API_BASE}/api/system/pollers/status"
    return _http_request(url, method="GET")


# -------------------------------------------------------------
# AGENT REMEDIATION REFLEX CACHE CLIENT (STRY0824901)
# -------------------------------------------------------------

def record_remediation(
    tool_name: str,
    failed_payload: str,
    error_snippet: str,
    successful_payload: Optional[str] = None,
    remediation_hint: Optional[str] = None,
    subsystem: str = "general"
) -> Dict[str, Any]:
    """Record a tool failure or pair with subsequent successful resolution."""
    url = f"{PORTAL_API_BASE}/api/system/remediation/record"
    payload = {
        "tool_name": tool_name,
        "failed_payload": failed_payload,
        "error_snippet": error_snippet,
        "successful_payload": successful_payload,
        "remediation_hint": remediation_hint,
        "subsystem": subsystem
    }
    return _http_request(url, method="POST", data=payload)


def check_remediation(tool_name: str, payload: str) -> Dict[str, Any]:
    """Check if tool call matches a known failure pattern with a verified fix."""
    query = f"?tool_name={urllib.parse.quote(tool_name)}&payload={urllib.parse.quote(payload)}"
    url = f"{PORTAL_API_BASE}/api/system/remediation/check{query}"
    return _http_request(url, method="GET")


def get_top_remediations(limit: int = 10) -> Dict[str, Any]:
    """Retrieve top error remediation reflexes for agent context priming."""
    url = f"{PORTAL_API_BASE}/api/system/remediation/top?limit={limit}"
    return _http_request(url, method="GET")


# ==============================================================================
# SPORTS & TEAM METADATA SDK (PORT 8095 / PORT 8090)
# ==============================================================================

import threading
import time

_team_cache: Dict[str, Dict[str, Any]] = {}
_team_list: List[Dict[str, Any]] = []
_team_cache_expiry: float = 0.0
_team_cache_lock = threading.Lock()
TEAM_CACHE_TTL = 300.0  # 5 minutes


def _refresh_team_cache(force: bool = False) -> None:
    """Internal helper to load all sys_sports_team records into thread-safe memory."""
    global _team_cache, _team_list, _team_cache_expiry
    now = time.time()
    if not force and _team_list and now < _team_cache_expiry:
        return

    with _team_cache_lock:
        if not force and _team_list and now < _team_cache_expiry:
            return
        url = f"{PORTAL_API_BASE}/api/sports/teams"
        try:
            teams = _http_request(url, method="GET")
            if isinstance(teams, list):
                new_cache = {}
                for t in teams:
                    abbr = (t.get("team_abbr") or "").upper()
                    sport = (t.get("sport") or "").upper()
                    new_cache[f"{abbr}_{sport}"] = t
                    if abbr not in new_cache or sport == "MLB":
                        new_cache[abbr] = t
                _team_cache = new_cache
                _team_list = teams
                _team_cache_expiry = now + TEAM_CACHE_TTL
        except Exception:
            if not _team_list:
                pass


def get_sports_teams(sport: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all sports teams from the centralized REST service."""
    _refresh_team_cache()
    with _team_cache_lock:
        all_teams = list(_team_list)
    if sport:
        return [t for t in all_teams if t.get("sport", "").upper() == sport.upper()]
    return all_teams


def get_team(team_abbr: str, sport: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve full team metadata object by canonical team abbreviation."""
    if not team_abbr:
        return None
    clean_abbr = team_abbr.strip().upper()
    _refresh_team_cache()
    with _team_cache_lock:
        if sport:
            compound_key = f"{clean_abbr}_{sport.strip().upper()}"
            if compound_key in _team_cache:
                return _team_cache[compound_key]
        if clean_abbr in _team_cache:
            return _team_cache[clean_abbr]

    # Direct REST fallback on cache miss
    query = f"?sport={urllib.parse.quote(sport.strip().upper())}" if sport else ""
    url = f"{PORTAL_API_BASE}/api/sports/teams/{urllib.parse.quote(clean_abbr)}{query}"
    try:
        team_data = _http_request(url, method="GET")
        if team_data and "team_abbr" in team_data:
            with _team_cache_lock:
                _team_cache[clean_abbr] = team_data
                _team_list.append(team_data)
            return team_data
    except Exception:
        pass
    return None


def get_team_color(team_abbr: str, fallback: str = "#00e5ff", secondary: bool = False, sport: Optional[str] = None) -> str:
    """
    Retrieve canonical primary or secondary hex color for a sports team.
    Guarantees non-empty hex return without hardcoded inline dictionaries.
    """
    team = get_team(team_abbr, sport=sport)
    if team:
        color_key = "secondary_color" if secondary else "primary_color"
        return team.get(color_key) or fallback
    return fallback


def resolve_team_name(name_or_keyword: str, sport: Optional[str] = "MLB") -> str:
    """
    Dynamically resolve a city, mascot, or alias string to canonical abbreviation.
    Replaces static duplicate dictionaries (TEAM_MAP, GLOBAL_TEAM_MAP).
    """
    if not name_or_keyword:
        return "GLOBAL"
    token = name_or_keyword.strip()

    # 1. Fast path: Direct cache abbreviation check
    _refresh_team_cache()
    upper_token = token.upper()
    with _team_cache_lock:
        if sport:
            compound_key = f"{upper_token}_{sport.strip().upper()}"
            if compound_key in _team_cache:
                return _team_cache[compound_key]["team_abbr"]
        if upper_token in _team_cache:
            return _team_cache[upper_token]["team_abbr"]

    # 2. Query REST resolution endpoint
    url = f"{PORTAL_API_BASE}/api/sports/teams/resolve"
    try:
        res = _http_request(url, method="POST", data={"query": token, "sport": sport})
        if res.get("resolved") and res.get("team_abbr"):
            return res.get("team_abbr")
    except Exception:
        pass

    # 3. In-memory alias scan across cached synonyms
    lower_token = token.lower()
    with _team_cache_lock:
        for t in _team_list:
            if sport and t.get("sport", "").upper() != sport.upper():
                continue
            if lower_token == t.get("name", "").lower() or lower_token == t.get("city", "").lower() or lower_token == t.get("full_name", "").lower():
                return t["team_abbr"]
            for syn in t.get("synonyms", []):
                s = syn.lower()
                if s == lower_token or re.search(r'\b' + re.escape(s) + r'\b', lower_token):
                    return t["team_abbr"]

    return "GLOBAL"


# ==============================================================================
# SOVEREIGN INTELLIGENCE RADAR (SIR) CLIENT SDK
# ==============================================================================

def sir_list_alerts(limit: int = 50, vertical: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve prioritized SIR regulatory & municipal intelligence alerts."""
    params = f"?limit={limit}"
    if vertical:
        params += f"&vertical={urllib.parse.quote(vertical)}"
    url = f"{PORTAL_API_BASE}/api/sir/alerts{params}"
    res = _http_request(url, method="GET")
    return res.get("alerts", [])

def sir_trigger_sweep(mock: bool = True) -> Dict[str, Any]:
    """Trigger on-demand SIR regulatory docket sweep."""
    url = f"{PORTAL_API_BASE}/api/sir/sweep?mock={'true' if mock else 'false'}"
    return _http_request(url, method="POST")

def sir_get_status() -> Dict[str, Any]:
    """Retrieve SIR indexed docket and alert inventory counts."""
    url = f"{PORTAL_API_BASE}/api/sir/status"
    return _http_request(url, method="GET")


# ==============================================================================
# MARD EDITORIAL COUNCIL CHAMBER SDK (WO0010234)
# ==============================================================================

def mard_run_editorial_deliberation(topic: str, dry_run: bool = False, model: str = "gemini-3.8-flash") -> Dict[str, Any]:
    """
    Executes automated multi-agent deliberation between WildSeed advocates
    (Compliance Karen, Dab Lab Derek, Dr. Terp, 420 Linda, Michael Mclaren),
    extracts domain critiques, and synthesizes a publication-ready Field Notes essay.
    """
    from scripts.mard_editorial_chamber import get_gemini_client, run_council_deliberation
    from pathlib import Path

    client = get_gemini_client()
    result = run_council_deliberation(client, topic, preferred_model=model)

    if not dry_run:
        slug = result.get("title", "essay").lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:30]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        incoming_dir = Path("/home/james/sovereign_inbox/queue/incoming")
        incoming_dir.mkdir(parents=True, exist_ok=True)
        wo_path = incoming_dir / f"WO_AUTO_ESSAY_{ts}_{slug}.json"
        wo_path.write_text(json.dumps(result, indent=2))
        result["staged_path"] = str(wo_path)

    return result


# ==============================================================================
# PROSPECT RECON SENTINEL SDK (TOOL #49)
# ==============================================================================

def get_recon_prospects() -> List[Dict[str, Any]]:
    """Retrieve all audited prospects from the Recon Sentinel REST API."""
    url = f"{PORTAL_API_BASE}/api/recon/prospects"
    return _http_request(url, method="GET")

def get_recon_prospect_detail(slug: str) -> Dict[str, Any]:
    """Retrieve prospect detail, audit runs, target keywords, and SERP results via REST API."""
    url = f"{PORTAL_API_BASE}/api/recon/prospects/{urllib.parse.quote(slug)}"
    return _http_request(url, method="GET")


# ==============================================================================
# PERSONA TRUTHS & SWARM COUNCIL SDK
# ==============================================================================

def upsert_persona_truth(handle: str, display_name: str, role: str, truth: str,
                         domain: str = "DAVINCIS_SMYRNA", is_heel: bool = False) -> Dict[str, Any]:
    """Upsert a canonical persona truth into persona_truths via FastAPI."""
    url = f"{PORTAL_API_BASE}/api/personas/truth"
    payload = {
        "handle": handle,
        "display_name": display_name,
        "role": role,
        "truth": truth,
        "domain": domain,
        "is_heel": is_heel
    }
    return _http_request(url, method="POST", data=payload)

def get_persona_truths(domain: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve canonical persona truths from persona_truths table via FastAPI."""
    params = ""
    if domain:
        params = f"?{urllib.parse.urlencode({'domain': domain})}"
    url = f"{PORTAL_API_BASE}/api/personas/truths{params}"
    return _http_request(url, method="GET")

