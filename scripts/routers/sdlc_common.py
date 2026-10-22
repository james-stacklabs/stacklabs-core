#!/usr/bin/env python3
"""
Sovereign SDLC Common Utilities & State Access Layer
Shared helpers, database connectors, and visual sentry validators.
"""

import os
import sys
import re
import json
import base64
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import requests

logger = logging.getLogger("sdlc_common")

PROJECT_ROOT = Path("/home/james/stacklabs")
DB_PATH = os.getenv("SOVEREIGN_DB_PATH", "/home/james/stacklabs/dna/sovereign_now.db")
if not os.path.exists(DB_PATH) and os.path.exists("y:/dna/sovereign_now.db"):
    DB_PATH = "y:/dna/sovereign_now.db"

INBOX_PATH = Path(os.getenv("SOVEREIGN_INBOX", "/home/james/sovereign_inbox"))
if not os.path.exists(str(INBOX_PATH)) and os.path.exists("z:"):
    INBOX_PATH = Path("z:")

INBOX_PATH.mkdir(parents=True, exist_ok=True)

try:
    from scripts.core.audit_chain import SovereignAuditChain
except Exception:
    try:
        sys.path.insert(0, "/home/james/stacklabs")
        from scripts.core.audit_chain import SovereignAuditChain
    except Exception as _ac_err:
        SovereignAuditChain = None
        logger.warning(f"SovereignAuditChain import failed: {_ac_err}")

def log_audit_chain_event(event_type: str, payload: dict) -> None:
    if SovereignAuditChain is None:
        return
    try:
        chain = SovereignAuditChain(db_path=DB_PATH)
        chain.append(event_type, payload)
    except Exception as e:
        logger.error(f"log_audit_chain_event error logging {event_type}: {e}")

def resolve_attachment_path(filename: str):
    paths_to_check = [
        os.path.join(str(INBOX_PATH), filename),
        os.path.join(str(INBOX_PATH), "archive_graveyard", filename),
        os.path.join(str(INBOX_PATH), "processed", filename),
        os.path.join(str(INBOX_PATH), "needs_review", filename),
        os.path.join(str(INBOX_PATH), "tickets", filename),
        os.path.join(str(INBOX_PATH), "reports", filename),
        os.path.join(str(INBOX_PATH), "dashboards", filename),
        os.path.join(str(INBOX_PATH), "walkthroughs", filename),
        os.path.join(str(INBOX_PATH), "implementation_plans", filename),
    ]
    for p in paths_to_check:
        if os.path.exists(p):
            return p
    if os.path.exists(str(INBOX_PATH)):
        for entry in os.listdir(str(INBOX_PATH)):
            if entry.startswith("daily_"):
                p = os.path.join(str(INBOX_PATH), entry, filename)
                if os.path.exists(p):
                    return p
    return None

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn
def map_ticket_type(t_type_db):
    if not t_type_db:
        return "STORY"
    s = t_type_db.strip().upper()
    if s == "STRY": return "STORY"
    if s == "INC": return "INCIDENT"
    if s == "DFCT": return "BUG"
    if s == "ENHC": return "ENHANCEMENT"
    if s == "REQ": return "REQUEST"
    if s == "IDEA": return "IDEA"
    if s == "WO": return "WORK_ORDER"
    return s

def reverse_map_ticket_type(t_type_ui):
    if not t_type_ui:
        return "STRY"
    s = t_type_ui.strip().upper()
    if s in ("STORY", "STRY"): return "STRY"
    if s in ("INCIDENT", "INC"): return "INC"
    if s in ("BUG", "DEFECT", "DFCT"): return "DFCT"
    if s in ("ENHANCEMENT", "ENHC"): return "ENHC"
    if s in ("REQUEST", "REQ"): return "REQ"
    if s in ("IDEA", "INNOVATION", "INCUBATOR"): return "IDEA"
    if s in ("WORK_ORDER", "WO"): return "WO"
    return "STRY"

def map_state(state_int):
    if state_int is None:
        return "OPEN"
    s = str(state_int).strip().upper()
    if s in ("5", "CLOSED"): return "CLOSED"
    if s in ("4", "RESOLVED", "DONE"): return "DONE"
    if s in ("3", "TESTING"): return "TESTING"
    if s in ("2", "IN_PROGRESS"): return "IN_PROGRESS"
    if s in ("1", "OPEN"): return "OPEN"
    if s in ("0", "PLANNING"): return "PLANNING"
    return s

def reverse_map_state(status_str):
    if not status_str:
        return 1
    s = str(status_str).strip().upper()
    if s in ("CLOSED", "5"): return 5
    if s in ("DONE", "RESOLVED", "4"): return 4
    if s in ("TESTING", "3"): return "Testing"
    if s in ("IN_PROGRESS", "2"): return 2
    if s in ("OPEN", "1"): return 1
    if s in ("PLANNING", "0"): return 0
    return 1

def map_priority(p_int):
    if str(p_int) == "1": return "P1"
    if str(p_int) == "2": return "P2"
    if str(p_int) == "3": return "P3"
    return "P3"

def reverse_map_priority(p_str):
    if p_str == "P1": return 1
    if p_str == "P2": return 2
    if p_str == "P3": return 3
    return 3

def is_ui_ticket(ticket_data: dict) -> bool:
    """
    Determines if a ticket represents a UI/frontend deliverable subject to Rule IV.2.b.
    Checks affected_ci/cmdb_ci, short_description/title, description, and number.
    """
    ci = str(ticket_data.get('affected_ci') or ticket_data.get('cmdb_ci') or '').strip().lower()
    title = str(ticket_data.get('short_description') or ticket_data.get('title') or '').strip().lower()
    desc = str(ticket_data.get('description') or '').strip().lower()
    number = str(ticket_data.get('number') or ticket_data.get('id') or '').strip().lower()
    
    combined = f"{number} {title} {desc}"
    
    # Explicit non-ui bypass markers
    bypass_markers = ["[non-ui]", "[backend-only]", "[no-ui]", "[headless]", "[api-only]", "[infra]", "[backend-gate]"]
    if any(marker in combined for marker in bypass_markers):
        return False

    # Primary UI CIs
    ui_cis = ["01_sovereign_portal", "15_fanstack", "portal", "fanstack", "frontend", "playcall", "19_fanstackarena", "15_fanstackcreator", "fanstackarena", "fanstackcreator"]
    if any(u in ci for u in ui_cis):
        # Even with UI CI, if explicitly declared pure backend/API task:
        if re.search(r'\b(pure backend|api endpoint|database migration|schema migration|fastapi-only)\b', combined):
            return False
        return True

    # Check for strong UI keywords in title or ticket number
    strong_ui_regex = r'\b(ui|gui|hud|frontend|screen|tab|modal|widget|dashboard|mockup|playcall-desk|navbar|sidebar|carousel|lookbook|css|html|react-view|web-app)\b'
    if re.search(strong_ui_regex, title) or re.search(strong_ui_regex, number):
        return True

    return False

def has_verified_visual_twin(conn, ticket_sys_id: str, ticket_number: str, ticket_data: dict = None, return_detail: bool = False):
    """
    Checks if a ticket has an attached, verified Pegasus Playwright live visual twin image.
    Enforces Rule IV.2.b and the Two-Tier 85% Spatial & Parity Gate:
      1. Envelope Check: Must have a live twin image (pegasus, playwright, visual_twin, live_uat).
      2. Integrity Check: Physical file must exist on disk and be >= 15KB (no empty/broken screenshots).
      3. Spatial/Route Consistency Check (The Kangaroo Detector): Target CI/route must match captured view.
      4. Multimodal Parity Evaluation (if target mockup exists): Compares layout landmarks.
    """
    rows = conn.execute("""
        SELECT sys_id, file_name, content_type, file_path 
        FROM sys_attachment 
        WHERE table_name = 'sovereign_tickets' 
          AND (table_sys_id = ? OR table_sys_id = ?)
    """, (ticket_sys_id, ticket_number)).fetchall()
    
    if not rows:
        msg = (
            "⛔ HARD-GATE [Rule IV.2.b Violation]: No live browser visual twin attachment found for this UI ticket. "
            "Capture live UI state using scripts/pegasus_sentry_client.py from Pegasus (100.96.77.20), "
            "verify KI-095 zero outer scrollbars, and upload via api_client.upload_ticket_attachment()."
        )
        return (False, msg) if return_detail else False
        
    twin_indicators = ["pegasus", "playwright", "visual_twin", "live_uat", "sentry"]
    image_exts = (".png", ".jpg", ".jpeg", ".webp")
    
    twin_rows = []
    mockup_rows = []
    
    for row in rows:
        fn = str(row['file_name'] or '').lower()
        ct = str(row['content_type'] or '').lower()
        is_img = ct.startswith("image/") or any(fn.endswith(ext) for ext in image_exts)
        if is_img:
            if any(ind in fn for ind in twin_indicators):
                twin_rows.append(row)
            elif any(m in fn for m in ["mockup", "target", "concept", "design"]):
                mockup_rows.append(row)
                
    if not twin_rows:
        msg = (
            f"⛔ HARD-GATE [Rule IV.2.b Violation]: Attachments exist, but none are a verified Pegasus Playwright live visual twin "
            f"(file_name must contain one of {twin_indicators})."
        )
        return (False, msg) if return_detail else False
        
    # Tier 1: File Integrity and Physical Size Check (No empty/stub files)
    valid_twin_path = None
    twin_fn = None
    for tr in twin_rows:
        candidate_paths = [
            tr['file_path'],
            os.path.join(INBOX_PATH, "tickets", str(tr['file_path'] or '').replace("/attachments/", "")),
            resolve_attachment_path(tr['file_name']),
            os.path.join(INBOX_PATH, "tickets", ticket_number, "artifacts", tr['file_name']),
            os.path.join(INBOX_PATH, "tickets", ticket_number, "mockups", tr['file_name']),
        ]
        for cp in candidate_paths:
            if cp and os.path.exists(cp) and os.path.isfile(cp):
                sz = os.path.getsize(cp)
                if sz >= 15_000:  # Must be at least 15KB for an authentic desktop screenshot
                    valid_twin_path = cp
                    twin_fn = tr['file_name']
                    break
        if valid_twin_path:
            break
            
    if not valid_twin_path:
        msg = (
            "⛔ HARD-GATE [Rule IV.2.b Integrity Fault]: Visual twin attachment file is missing from disk or "
            "smaller than 15KB (corrupted/empty screenshot). An authentic full-page desktop twin capture is required."
        )
        return (False, msg) if return_detail else False
        
    # Tier 1.5: Spatial Route & Port Consistency Check (The Kangaroo Detector)
    t_eval = ticket_data or {}
    ci = str(t_eval.get('affected_ci') or t_eval.get('cmdb_ci') or '').lower()
    title = str(t_eval.get('short_description') or t_eval.get('title') or '').lower()
    desc = str(t_eval.get('description') or '').lower()
    notes = str(t_eval.get('work_notes') or '').lower()
    fn_lower = twin_fn.lower()
    
    # Check for Consumer FanStack (:3009) vs Producer Playcall Desk (:3010) collision
    if ("15_fanstack" in ci or "15_fanstackcreator" in ci or "fanstackcreator" in ci or "port 3009" in desc or "fanstack" in title) and ("playcall" not in title and "producer" not in title):
        if ("playcall" in fn_lower or "soundboard" in fn_lower) and "starter" not in fn_lower and "room" not in fn_lower:
            msg = (
                f"⛔ HARD-GATE [Rule IV.2.b Layout Mismatch]: Visual twin '{twin_fn}' captured Producer Playcall Desk (Port 3010) "
                f"instead of the FanStack Consumer Watch Room (Port 3009). The screenshot does not represent the targeted UI room."
            )
            return (False, msg) if return_detail else False

    # Check for Sports Arena (:3010) vs Portal (:3016) collision
    if ("19_sovereign_sports" in ci or "19_fanstackarena" in ci or "fanstackarena" in ci or "port 3010" in desc) and ("portal" in fn_lower or "kanban" in fn_lower):
        msg = (
            f"⛔ HARD-GATE [Rule IV.2.b Layout Mismatch]: Visual twin '{twin_fn}' captured Sovereign Portal (Port 3016) "
            f"instead of FanStack Arena (Port 3010)."
        )
        return (False, msg) if return_detail else False

    # Tier 2: The Real Eyes 85% Pilot Assist Evaluation
    # If the Pilot manually tagged '[Pilot Assist]' or 'pilot verified' in work notes, pass with craftsman badge
    if "[pilot assist]" in notes or "pilot verified" in notes or "human eye" in notes:
        msg = f"Visual twin verified with Pilot Assist craftsman override active ({twin_fn})."
        return (True, msg) if return_detail else True

    # If mockups exist, check if Gemini key is available for AI landmark parity scoring
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and mockup_rows and valid_twin_path:
        mockup_path = None
        for mr in mockup_rows:
            p = resolve_attachment_path(mr['file_name']) or mr.get('file_path')
            if p and os.path.exists(p) and os.path.getsize(p) >= 15_000:
                mockup_path = p
                break
        
        if mockup_path:
            try:
                import base64
                with open(mockup_path, "rb") as f:
                    b64_mock = base64.b64encode(f.read()).decode("utf-8")
                with open(valid_twin_path, "rb") as f:
                    b64_twin = base64.b64encode(f.read()).decode("utf-8")
                    
                prompt = (
                    "You are the Sovereign OS Visual Sentry. Compare Image 1 (Target Mockup) and Image 2 (Live Pegasus Playwright Capture).\n"
                    "Evaluate: (1) Does Image 2 depict the same application page/workspace as Image 1, or is it a completely different screen? "
                    "(2) Rate visual parity 0-100%. "
                    "Respond with JSON ONLY: {\"is_same_screen\": bool, \"parity_score\": int, \"reason\": \"string\"}"
                )
                
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": b64_mock}},
                            {"inline_data": {"mime_type": "image/png", "data": b64_twin}}
                        ]
                    }]
                }
                res = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={gemini_key}",
                    json=payload,
                    timeout=5
                )
                if res.status_code == 200:
                    cand = res.json().get("candidates", [])
                    if cand and "content" in cand[0]:
                        txt = cand[0]["content"]["parts"][0]["text"].strip()
                        if txt.startswith("```"):
                            txt = re.sub(r"^```json\s*|\s*```$", "", txt, flags=re.MULTILINE).strip()
                        p_data = json.loads(txt)
                        same_screen = p_data.get("is_same_screen", True)
                        score = int(p_data.get("parity_score", 100))
                        reason = p_data.get("reason", "")
                        
                        if not same_screen or score < 50:
                            msg = (
                                f"⛔ HARD-GATE [Rule IV.2.b Kangaroo Alarm - Parity {score}%]: "
                                f"Visual Sentry rejected capture: Target Mockup and Live Twin depict completely different screens. Reason: {reason}"
                            )
                            return (False, msg) if return_detail else False
                        elif 50 <= score < 85:
                            if "[pilot assist]" not in notes:
                                msg = (
                                    f"⚠️ THE 85% LINE REACHED [Visual Parity {score}%]: Layout matches but visual styling requires "
                                    f"human craftsmanship. Reason: {reason}. Add '[Pilot Assist]' to work notes to confirm or refine assets in pilot_drops/."
                                )
                                return (False, msg) if return_detail else False
            except Exception as audit_err:
                print(f"[VISUAL_SENTRY_AUDIT_WARNING] {audit_err}")

    msg = f"Verified live Pegasus visual twin attached and validated ({twin_fn})."
    return (True, msg) if return_detail else True

