from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil, socket
from datetime import datetime, timedelta, timezone
import bcrypt
from pathlib import Path
from core.db import DB_PATH, get_db
from core.security import (
    get_current_user, require_pilot, require_manager_or_pilot, security,
    _check_rate_limit, _get_user_from_db, _get_user_modules, _create_token, _decode_token,
)

router = APIRouter()

# ----------------------------------------------------
# CREATOR LOGIN TELEMETRY WIRETAP (WO-2026-0910-CLOUDFLARE-TUNNEL-LOGIN-WIRETAP)
# ----------------------------------------------------

async def trigger_govee_creator_pulse():
    """Strobe living room Govee light strips in Mets Blue & Orange for 3 seconds, then restore baseline."""
    port = int(os.getenv("GOVEE_PORT", 4003))
    ips = ["192.168.1.173", "192.168.1.174", "192.168.1.176", "192.168.1.188"]
    env_ips = os.getenv("GOVEE_IPS")
    if env_ips:
        ips = [ip.strip() for ip in env_ips.split(",") if ip.strip()]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    def send_color(r, g, b):
        msg = {
            "msg": {
                "cmd": "colorWC",
                "data": {
                    "color": {"r": r, "g": g, "b": b},
                    "colorTem": 0
                }
            }
        }
        payload = json.dumps(msg).encode("utf-8")
        for ip in ips:
            try:
                sock.sendto(payload, (ip, port))
            except Exception as e:
                pass

    try:
        print(f"✨ [GOVEE WIRETAP] Strobing Mets Blue & Orange on {ips} (Port {port})...", flush=True)
        # Strobe Mets Blue (0, 45, 98) & Mets Orange (252, 92, 29) for 3 seconds (5 iterations @ 300ms)
        for _ in range(5):
            send_color(0, 45, 98)
            await asyncio.sleep(0.3)
            send_color(252, 92, 29)
            await asyncio.sleep(0.3)
        # Restore baseline warm white
        send_color(255, 255, 255)
        print("✨ [GOVEE WIRETAP] Pulse complete. Baseline restored.", flush=True)
        return True
    except Exception as e:
        print(f"[GOVEE WIRETAP ERROR] {e}", flush=True)
        return False
    finally:
        sock.close()

def get_user_friendly_title(user_name: str, display_name: str = "", role: str = "", favorite_team: str = "") -> str:
    """Construct human-readable VIP / Friend & Family target identifier."""
    u_lower = user_name.lower().strip()
    d_name = display_name.strip() if display_name else user_name
    
    # Specific known VIPs / Friends & Family mappings
    if u_lower in ("barb", "barbbaker", "barb_baker"):
        return f"Barb Baker (@{user_name} • Girlfriend / Patron / NYM)"
    elif u_lower in ("sean", "sean_carroll"):
        return f"Sean Carroll (@{user_name} • Brother / NYM)"
    elif u_lower in ("eileen", "eileen_carroll"):
        return f"Eileen Carroll (@{user_name} • Mom / NYM)"
    elif u_lower in ("allyson", "allyson_jarrett", "allyson_carroll", "allison", "allison_carroll", "allison_jarrett"):
        return f"Allyson Jarrett (@{user_name} • Sister / NYY)"
    elif u_lower in ("jeff", "jeff_carroll"):
        return f"Jeff Carroll (@{user_name} • NYM)"
    elif u_lower in ("patsy", "aunt_patsy", "auntpatsy", "patricia"):
        return f"Aunt Patsy (@{user_name} • Aunt / NYM)"
    elif u_lower in ("jose",):
        return f"Jose (@{user_name} • NYM)"
    elif u_lower in ("jmalone", "jeremymalone"):
        return f"Jeremy Malone (@{user_name} • STL)"
    elif u_lower in ("jwalker", "jeremywalker"):
        return f"Jeremy Walker (@{user_name} • STL)"
    elif u_lower in ("wardynym", "tylerward", "wardy"):
        return f"Tyler Ward (@{user_name} • Creator)"
    else:
        role_label = role.capitalize() if role else "Guest"
        team_suffix = f" / {favorite_team.upper()}" if favorite_team else ""
        return f"{d_name} (@{user_name} • {role_label}{team_suffix})"


async def broadcast_user_login_websocket(user_name: str, display_name: str, target_title: str, formatted_time: str):
    """Broadcast real-time toast and system announcement over Port 8008 WebSocket mesh."""
    try:
        import websockets
        async with websockets.connect("ws://127.0.0.1:8008") as ws:
            # 1. System Chat Announcement to all game rooms
            await ws.send(json.dumps({
                "type": "CHAT_MESSAGE",
                "user": "SYSTEM",
                "color": "#00f0ff",
                "text": f"🔔 {display_name} has entered the stadium!",
                "target_game_pk": "GLOBAL"
            }))
            # 2. Specific structured USER_LOGIN_ALERT event
            await ws.send(json.dumps({
                "type": "USER_LOGIN_ALERT",
                "user_name": user_name,
                "display_name": display_name,
                "target_title": target_title,
                "timestamp": formatted_time
            }))
            print(f"📡 [WIRETAP WS BROADCAST] Broadcasted login alert for {target_title} across mesh.", flush=True)
            return True
    except Exception as ws_err:
        print(f"[WIRETAP WS BROADCAST ERROR] {ws_err}", flush=True)
        return False


async def trigger_creator_notification(user_name: str, ip_address: str, user_agent: str, user_meta: dict = None):
    """Dispatch instant priority wiretap alert to Pilot via outbound dispatch mailer."""
    try:
        send_dispatch_fn = None
        try:
            from send_dispatch_report import send_dispatch as s_fn
            send_dispatch_fn = s_fn
        except ImportError:
            try:
                from scripts.send_dispatch_report import send_dispatch as s_fn
                send_dispatch_fn = s_fn
            except ImportError:
                pass

        if not send_dispatch_fn:
            print("[WIRETAP NOTIFICATION] send_dispatch_report not importable, skipping email dispatch.", flush=True)
            return False

        meta = user_meta or {}
        display_name = meta.get("display_name") or user_name
        email = meta.get("email") or "Not registered"
        role = meta.get("role") or "Guest"
        fav_team = meta.get("favorite_team") or ""

        target_title = get_user_friendly_title(user_name, display_name, role, fav_team)

        # Compute America/New_York human-readable timestamp
        try:
            import zoneinfo
            ny_tz = zoneinfo.ZoneInfo("America/New_York")
        except Exception:
            ny_tz = None
        now_ny = datetime.now(ny_tz)
        formatted_time = now_ny.strftime("%A, %b %d, %Y • %I:%M:%S %p %Z")

        subject = f"🚨 [GUEST LOGIN ALERT] {target_title} Authenticated to Sovereign OS"
        body = (
            f"=======================================================\n"
            f"🚨 SOVEREIGN OS AUTHENTICATION WIRETAP ALERT\n"
            f"=======================================================\n\n"
            f"Guest Authenticated:\n"
            f"• Target Callsign: {target_title}\n"
            f"• Full Name:       {display_name}\n"
            f"• Username:        @{user_name}\n"
            f"• Email:           {email}\n"
            f"• Role:            {role}\n"
            f"• Allegiance:      {fav_team or 'Neutral'}\n"
            f"• Client IP:       {ip_address}\n"
            f"• User Agent:      {user_agent}\n"
            f"• Timestamp:       {formatted_time}\n\n"
            f"Multi-Channel Dispatches Executed:\n"
            f"• Living Room Govee LEDs strobed in Mets Blue & Orange (Port 4003).\n"
            f"• Real-time entrance toast broadcast to active watch parties (Port 8008).\n"
            f"• Session audit entry committed to sovereign_now.db.creator_access_audit.\n\n"
            f"Active Public Gateways (Cloudflare Tunnels):\n"
            f"• StackLabs Listen:               https://listen.stacklabsllc.com\n"
            f"• FanStack Creator Portal:        https://creator.stacklabsllc.com\n"
            f"• Model Battle Arena:             https://arena.stacklabsllc.com\n"
            f"• Public Watch Room:              https://watch.stacklabsllc.com\n"
        )
        loop = asyncio.get_running_loop()
        recipients = ["james@stacklabsllc.com", "stacklabs.edge@gmail.com"]
        dispatched = []
        for rcpt in recipients:
            try:
                ok = await loop.run_in_executor(None, lambda target=rcpt: send_dispatch_fn(subject=subject, body=body, recipient=target))
                dispatched.append(bool(ok))
            except Exception as mail_err:
                print(f"[WIRETAP NOTIFICATION ERROR - {rcpt}] {mail_err}", flush=True)
        print(f"📧 [WIRETAP NOTIFICATION] Email alerts dispatched to {recipients}: {dispatched}", flush=True)
        return any(dispatched)
    except Exception as e:
        print(f"[WIRETAP NOTIFICATION ERROR] {e}", flush=True)
        return False


async def execute_creator_wiretap(user_name: str, ip_address: str, user_agent: str):
    """Asynchronous non-blocking orchestrator for guest login telemetry wiretap."""
    audit_id = uuid.uuid4().hex
    print(f"\n🚨🚨 [GUEST WIRETAP ACTIVATED] User '{user_name}' login intercepted! Launching asynchronous pulse & alert...\n", flush=True)

    # 1. Hydrate user metadata from sys_user
    user_meta = {}
    try:
        with get_db() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT display_name, email, role, favorite_team FROM sys_user WHERE LOWER(user_name) = LOWER(?) LIMIT 1",
                (user_name,)
            ).fetchone()
            if row:
                user_meta = dict(row)
    except Exception as e:
        print(f"[WIRETAP USER LOOKUP ERROR] {e}", flush=True)

    display_name = user_meta.get("display_name") or user_name
    role = user_meta.get("role") or "Guest"
    fav_team = user_meta.get("favorite_team") or ""
    target_title = get_user_friendly_title(user_name, display_name, role, fav_team)

    try:
        import zoneinfo
        ny_tz = zoneinfo.ZoneInfo("America/New_York")
    except Exception:
        ny_tz = None
    now_ny = datetime.now(ny_tz)
    formatted_time = now_ny.strftime("%A, %b %d, %Y • %I:%M:%S %p %Z")

    # 2. Database Log
    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO creator_access_audit 
                (sys_id, user_name, ip_address, user_agent, access_time, login_status, wiretap_dispatched, govee_strobe_status, notification_status)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'SUCCESS', 1, 'IN_PROGRESS', 'IN_PROGRESS')
                """,
                (audit_id, user_name, ip_address, user_agent)
            )
            conn.commit()
    except Exception as e:
        print(f"[WIRETAP DB INSERT ERROR] {e}", flush=True)

    # 3. Concurrently fire Govee strobe pulse, email alert, and WebSocket announcement
    govee_res, notify_res, ws_res = await asyncio.gather(
        trigger_govee_creator_pulse(),
        trigger_creator_notification(user_name, ip_address, user_agent, user_meta),
        broadcast_user_login_websocket(user_name, display_name, target_title, formatted_time),
        return_exceptions=True
    )
    govee_status = "SUCCESS" if govee_res is True else "FAILED"
    notify_status = "SUCCESS" if notify_res is True else "FAILED"

    # 4. Update Audit Record Status
    try:
        with get_db() as conn:
            conn.execute(
                "UPDATE creator_access_audit SET govee_strobe_status = ?, notification_status = ? WHERE sys_id = ?",
                (govee_status, notify_status, audit_id)
            )
            conn.commit()
    except Exception as e:
        print(f"[WIRETAP DB UPDATE ERROR] {e}", flush=True)

class LoginRequest(BaseModel):
    username: str
    password: str

class ProvisionRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""
    role: str = "guest"
    email: str = ""

@router.post("/api/auth/login")
async def auth_login(req: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    user = _get_user_from_db(req.username)
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.checkpw(req.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    modules = _get_user_modules(user["user_name"])
    token = _create_token(user["user_name"], user["role"] or "guest", user["display_name"] or user["user_name"], modules)
    
    forwarded_for = request.headers.get("x-forwarded-for")
    effective_ip = forwarded_for.split(",")[0].strip() if forwarded_for else client_ip
    user_agent = request.headers.get("user-agent", "unknown")

    # Highly visible log alert for tracking external access
    print(f"\n\n=======================================================")
    print(f"[TARGET ACQUIRED] User '{user['user_name']}' successfully logged in!")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"IP Address: {effective_ip}")
    print(f"=======================================================\n\n", flush=True)

    # Trigger Guest / Non-Pilot Telemetry Wiretap for ANY user where user != 'james'
    is_pilot = user["user_name"].lower() in ("james", "pilot")
    if not is_pilot:
        asyncio.create_task(execute_creator_wiretap(user["user_name"], effective_ip, user_agent))
    
    return {"token": token, "user_name": user["user_name"], "role": user["role"], "display_name": user["display_name"], "modules": modules}

@router.get("/api/auth/creator_audit")
async def get_creator_access_audit():
    """Retrieve creator access audit log for monitoring and SDLC verification."""
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sys_id, user_name, ip_address, user_agent, access_time, 
                   login_status, wiretap_dispatched, govee_strobe_status, notification_status 
            FROM creator_access_audit 
            ORDER BY access_time DESC LIMIT 50
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
        return {"status": "success", "count": len(rows), "audits": rows}

@router.post("/api/auth/simulate_wiretap")
async def simulate_wiretap(request: Request, user_name: str = "sean"):
    """Simulate a guest login event to test wiretap, email, and Govee pulse end-to-end."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded_for = request.headers.get("x-forwarded-for")
    effective_ip = forwarded_for.split(",")[0].strip() if forwarded_for else client_ip
    user_agent = request.headers.get("user-agent", "Sovereign-Wiretap-Tester/1.0")

    await execute_creator_wiretap(user_name, effective_ip, user_agent)
    return {"status": "simulated", "user_name": user_name, "effective_ip": effective_ip}

# ----------------------------------------------------
# WILDSEED EDGE VISITOR WIRETAP BEACON (WO0010236)
# ----------------------------------------------------

def _ensure_visitor_telemetry_table():
    try:
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS visitor_telemetry_audit (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    city TEXT,
                    region TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT,
                    alert_dispatched INTEGER DEFAULT 0
                )
            """)
            conn.commit()
    except Exception as e:
        print(f"[VISITOR TELEMETRY TABLE INIT ERROR] {e}", flush=True)

_ensure_visitor_telemetry_table()

def _parse_device_summary(ua: str) -> str:
    if not ua:
        return "Unknown Device / Unknown OS"
    os_name = "Unknown OS"
    if "iPhone" in ua:
        os_name = "iOS (iPhone)"
    elif "iPad" in ua:
        os_name = "iPadOS"
    elif "Android" in ua:
        os_name = "Android"
    elif "Macintosh" in ua or "Mac OS X" in ua:
        os_name = "macOS"
    elif "Windows NT 10" in ua:
        os_name = "Windows 10/11"
    elif "Windows" in ua:
        os_name = "Windows"
    elif "Linux" in ua:
        os_name = "Linux"

    browser_name = "Browser"
    if "Edg/" in ua:
        browser_name = "Edge"
    elif "Chrome/" in ua and "Edg/" not in ua:
        browser_name = "Chrome"
    elif "Firefox/" in ua:
        browser_name = "Firefox"
    elif "Safari/" in ua and "Chrome" not in ua:
        browser_name = "Safari"
    elif "curl" in ua.lower():
        browser_name = "curl"
    elif "playwright" in ua.lower():
        browser_name = "Playwright"

    return f"{os_name} / {browser_name}"

def _is_pilot_local_ip(ip: str) -> bool:
    if not ip:
        return False
    clean_ip = ip.strip()
    if clean_ip in ("127.0.0.1", "::1", "localhost", "0.0.0.0"):
        return True
    if clean_ip.startswith("192.168.") or clean_ip.startswith("10.") or clean_ip.startswith("100."):
        return True
    if clean_ip.startswith("172."):
        parts = clean_ip.split(".")
        if len(parts) >= 2 and parts[1].isdigit():
            sec = int(parts[1])
            if 16 <= sec <= 31:
                return True
    return False

async def _dispatch_wildseed_beacon_email(
    city: str,
    region: str,
    country: str,
    event: str,
    details_str: str,
    device_summary: str,
    ip: str,
    timestamp_ny: str,
    details: dict = None
):
    """Dispatch instant priority alert email via scripts/send_dispatch_report.py."""
    try:
        send_dispatch_fn = None
        try:
            from send_dispatch_report import send_dispatch as s_fn
            send_dispatch_fn = s_fn
        except ImportError:
            try:
                from scripts.send_dispatch_report import send_dispatch as s_fn
                send_dispatch_fn = s_fn
            except ImportError:
                pass

        if not send_dispatch_fn:
            print("[WILDSEED BEACON EMAIL] send_dispatch_report not importable, skipping email dispatch.", flush=True)
            return False

        if details is None:
            try:
                details = json.loads(details_str) if details_str else {}
            except Exception:
                details = {}

        if not isinstance(details, dict):
            details = {}

        if event == "voice_problem_drop":
            drop_id = details.get("drop_id", "UNKNOWN")
            partner = details.get("partner", "guest")
            problem = details.get("problem_statement", "")
            memo = details.get("council_memo", "")
            subject = f"🚨 [FORGE DROP RECEIVED] {drop_id} — {partner}"
            body = (
                f"🚨 FORGE PROBLEM DROP RECEIVED\n"
                f"==================================================\n"
                f"Partner / Sender: {partner.upper()}\n"
                f"Drop ID:          {drop_id}\n"
                f"Location:         {city}, {region} ({country})\n"
                f"IP Address:       {ip}\n"
                f"Timestamp:        {timestamp_ny}\n"
                f"Device / OS:      {device_summary}\n"
                f"Target Turnaround:< 4 Hours\n"
                f"==================================================\n\n"
                f"PROBLEM STATEMENT:\n"
                f"--------------------------------------------------\n"
                f"{problem}\n\n"
                f"MARD BLUEPRINT & DELIVERABLE:\n"
                f"--------------------------------------------------\n"
                f"{memo}\n"
                f"==================================================\n"
            )
        elif event == "drop_page_visit":
            partner = details.get("partner", "anonymous") if isinstance(details, dict) else "anonymous"
            route = details.get("route", "/drop") if isinstance(details, dict) else "/drop"
            referrer = details.get("referrer", "direct") if isinstance(details, dict) else "direct"
            credits_left = details.get("credits_left", "N/A") if isinstance(details, dict) else "N/A"
            is_drop_event = event in ("drop_page_visit", "voice_problem_drop")
            subject = f"🚨 [STACKLABS DROP WIRETAP] Visitor from {city}, {region} ({device_summary}) — {event}" if is_drop_event else f"🚨 [WILDSEED EDGE ALERT] Visitor from {city}, {region} ({device_summary}) — {event}"
            body = (
                f"🚨 STACKLABS DROP VISITOR WIRETAP\n"
                f"==================================================\n"
                f"Partner / Ingress: @{partner}\n"
                f"Route:             {route}\n"
                f"Location:          {city}, {region} ({country})\n"
                f"IP Address:        {ip}\n"
                f"Device / OS:       {device_summary}\n"
                f"Referrer:          {referrer}\n"
                f"Credits Left:      {credits_left}\n"
                f"Timestamp:         {timestamp_ny}\n"
                f"Live URL:          https://www.stacklabsllc.com{route}\n"
                f"==================================================\n"
            )
        else:
            is_drop_event = event in ("drop_page_visit", "voice_problem_drop")
            subject = f"🚨 [STACKLABS DROP WIRETAP] Visitor from {city}, {region} ({device_summary}) — {event}" if is_drop_event else f"🚨 [WILDSEED EDGE ALERT] Visitor from {city}, {region} ({device_summary}) — {event}"
            body = (
                f"🚨 WILDSEED EDGE VISITOR INTERCEPTED\n"
                f"--------------------------------------------------\n"
                f"Location:    {city}, {region} ({country})\n"
                f"Event:       {event}\n"
                f"Details:     {details_str}\n"
                f"Device / OS: {device_summary}\n"
                f"IP Address:  {ip}\n"
                f"Timestamp:   {timestamp_ny}\n"
                f"URL:         https://www.stacklabsllc.com/wildseed\n"
                f"--------------------------------------------------\n"
            )

        loop = asyncio.get_running_loop()
        recipients = ["james@stacklabsllc.com", "stacklabs.edge@gmail.com"]
        for rcpt in recipients:
            try:
                await loop.run_in_executor(None, lambda target=rcpt: send_dispatch_fn(subject=subject, body=body, recipient=target))
            except Exception as mail_err:
                print(f"[WILDSEED BEACON EMAIL ERROR - {rcpt}] {mail_err}", flush=True)
        print(f"📧 [WILDSEED BEACON] Alert email dispatched to {recipients}.", flush=True)
        return True
    except Exception as e:
        print(f"[WILDSEED BEACON EMAIL ORCHESTRATION ERROR] {e}", flush=True)
        return False

async def _broadcast_wildseed_beacon_ws(payload: dict):
    """Broadcast WebSocket notification across mesh Port 8008."""
    try:
        import websockets
        async with websockets.connect("ws://127.0.0.1:8008", open_timeout=2) as ws:
            await ws.send(json.dumps({
                "type": "WILDSEED_VISITOR_ALERT",
                **payload
            }))
            print("📡 [WILDSEED BEACON WS] Broadcasted WILDSEED_VISITOR_ALERT across mesh Port 8008.", flush=True)
            return True
    except Exception as ws_err:
        print(f"[WILDSEED BEACON WS ERROR] {ws_err}", flush=True)
        return False

@router.post("/api/wildseed_beacon")
async def wildseed_beacon(request: Request):
    """Edge visitor wiretap beacon ingress endpoint."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded_for = request.headers.get("x-forwarded-for")
    effective_ip = body.get("ip") or (forwarded_for.split(",")[0].strip() if forwarded_for else client_ip)
    
    city = body.get("city") or request.headers.get("cf-ipcity") or "Unknown City"
    region = body.get("region") or request.headers.get("cf-region") or "Unknown Region"
    country = body.get("country") or request.headers.get("cf-ipcountry") or "Unknown Country"
    user_agent = body.get("userAgent") or request.headers.get("user-agent", "")
    event = body.get("event", "page_view")
    details = body.get("details", {})
    details_str = json.dumps(details) if isinstance(details, (dict, list)) else str(details)
    device_summary = _parse_device_summary(user_agent)

    # Check for explicit testing flag
    is_test = bool(body.get("test") or body.get("is_test") or request.query_params.get("test") in ("1", "true", "True"))

    # HIGH-PRIORITY EMAIL ALERT POLICY:
    # Only dispatch email alerts for genuine high-value B2B lead events or forge drops.
    # Never spam email on routine page views, essay reads, UI testing, or visits from the Pilot's home region.
    HIGH_INTENT_EMAIL_EVENTS = {
        "wholesale_inquiry", "b2b_inquiry", "buyer_lead", "contact_submission",
        "drop_page_visit", "voice_problem_drop", "skew_doc_submission"
    }

    is_internal_ip = _is_pilot_local_ip(effective_ip) or effective_ip.startswith("100.") or effective_ip in ("127.0.0.1", "::1", "localhost")
    is_pilot_geo = is_internal_ip or (city in ("Smyrna", "Atlanta", "Marietta") and region in ("Georgia", "GA"))
    force_alert = bool(body.get("force_alert"))

    # Expand automated/test signature detection
    ua_lower = user_agent.lower()
    is_automated_or_test = (
        is_test or 
        ("playwright" in ua_lower) or 
        ("headless" in ua_lower) or 
        ("curl" in ua_lower) or 
        ("python-requests" in ua_lower) or 
        ("agy" in ua_lower) or
        (isinstance(details, dict) and details.get("is_test") is True) or
        (city == "Unknown City" and is_internal_ip)
    )

    is_forge_drop = (event == "voice_problem_drop")
    partner = details.get("partner", "anonymous") if isinstance(details, dict) else "anonymous"
    is_named_partner = partner and partner.lower() not in ("anonymous", "guest", "default", "none", "")

    if force_alert:
        should_email = True
    elif event == "drop_page_visit":
        # NEVER email for anonymous /drop visits or internal test runs!
        # ONLY email if a named partner route is visited from a real non-local IP
        should_email = is_named_partner and (not is_pilot_geo) and (not is_automated_or_test) and (city != "Unknown City")
    elif is_forge_drop:
        # Real problem drop submissions alert unless explicitly flagged as internal test
        should_email = not is_automated_or_test
    else:
        should_email = ((event in HIGH_INTENT_EMAIL_EVENTS) and (not is_pilot_geo) and (not is_automated_or_test))

    # Timestamp in America/New_York
    try:
        import zoneinfo
        ny_tz = zoneinfo.ZoneInfo("America/New_York")
    except Exception:
        ny_tz = None
    now_ny = datetime.now(ny_tz)
    timestamp_ny = now_ny.strftime("%A, %b %d, %Y • %I:%M:%S %p %Z")
    audit_id = f"WSB-{uuid.uuid4().hex[:12].upper()}"

    # Record entry in SQLite table visitor_telemetry_audit
    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO visitor_telemetry_audit 
                (id, timestamp, event_type, city, region, ip_address, user_agent, details, alert_dispatched)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (audit_id, timestamp_ny, event, city, region, effective_ip, user_agent, details_str, 1 if should_email else 0)
            )
            conn.commit()
    except Exception as db_err:
        print(f"[WILDSEED BEACON DB INSERT ERROR] {db_err}", flush=True)

    # If forge drop, append to scratch_pad.md
    if is_forge_drop:
        try:
            drop_id = details.get("drop_id", "DROP_UNKNOWN") if isinstance(details, dict) else "DROP_UNKNOWN"
            problem = details.get("problem_statement", "") if isinstance(details, dict) else ""
            memo = details.get("council_memo", "") if isinstance(details, dict) else ""
            partner = details.get("partner", "guest") if isinstance(details, dict) else "guest"
            scratchpad_path = Path("/home/james/sovereign_inbox/pilot_drops/scratch_pad.md")
            if scratchpad_path.exists():
                entry = (
                    f"\n\n### 🎙️ [FORGE DROP RECEIVED] {partner.upper()}\n"
                    f"- **Timestamp**: {timestamp_ny}\n"
                    f"- **Drop ID**: `{drop_id}`\n"
                    f"- **Problem**: \"{problem}\"\n"
                    f"- **MARD Blueprint**:\n"
                    f"```\n"
                    f"{memo}\n"
                    f"```\n"
                    f"- **Target Turnaround**: < 4 Hours\n"
                )
                with open(scratchpad_path, "a", encoding="utf-8") as sp:
                    sp.write(entry)
                print(f"📝 [FORGE DROP] Appended drop {drop_id} to scratch_pad.md", flush=True)
        except Exception as sp_err:
            print(f"[FORGE DROP SCRATCHPAD ERROR] {sp_err}", flush=True)

    # If drop page visit, ONLY append to scratch_pad.md if it is a real named partner!
    if event == "drop_page_visit":
        is_named_partner = partner and partner.lower() not in ("anonymous", "guest", "default", "none", "")
        if is_named_partner and not is_automated_or_test and not is_pilot_geo:
            try:
                route = details.get("route", "/drop") if isinstance(details, dict) else "/drop"
                scratchpad_path = Path("/home/james/sovereign_inbox/pilot_drops/scratch_pad.md")
                if scratchpad_path.exists():
                    entry = f"- **[DROP VISITOR WIRETAP]**: {city}, {region} ({device_summary}) on {route} [@{partner}] at {timestamp_ny}\n"
                    with open(scratchpad_path, "a", encoding="utf-8") as sp:
                        sp.write(entry)
                    print(f"📝 [DROP WIRETAP] Appended verified partner wiretap to scratch_pad.md: {route} [@{partner}]", flush=True)
            except Exception as sp_err:
                print(f"[DROP WIRETAP SCRATCHPAD ERROR] {sp_err}", flush=True)

    # If skew doc submission, save markdown document and append to scratchpad
    if event == "skew_doc_submission":
        try:
            wiretaps_dir = Path("/home/james/sovereign_inbox/pilot_drops/wiretaps/skew")
            wiretaps_dir.mkdir(parents=True, exist_ok=True)
            ts_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_path = wiretaps_dir / f"SKEW_DOC_{ts_slug}.md"
            if doc_path.exists():
                doc_path = wiretaps_dir / f"SKEW_DOC_{ts_slug}_{uuid.uuid4().hex[:4]}.md"

            word_count = details.get("word_count", 0) if isinstance(details, dict) else 0
            full_text = details.get("full_text", "") if isinstance(details, dict) else ""
            chairs = details.get("chairs", []) if isinstance(details, dict) else []
            chairs_str = ", ".join(chairs) if isinstance(chairs, list) else str(chairs)

            doc_content = (
                f"# 🎯 SKEW DOCUMENT WIRETAP SUBMISSION\n"
                f"- **Timestamp**: {timestamp_ny}\n"
                f"- **Origin**: {city}, {region}, {country} (IP: {effective_ip})\n"
                f"- **Device**: {device_summary}\n"
                f"- **Word Count**: {word_count}\n"
                f"- **Panelists**: {chairs_str}\n\n"
                f"---\n\n"
                f"## SUBMITTED DOCUMENT CONTENT\n\n"
                f"{full_text}\n"
            )
            doc_path.write_text(doc_content, encoding="utf-8")
            print(f"🕵️ [SKEW WIRETAP] Captured document ({word_count} words) -> {doc_path}", flush=True)

            scratchpad_path = Path("/home/james/sovereign_inbox/pilot_drops/scratch_pad.md")
            if scratchpad_path.exists():
                sp_entry = f"- **[SKEW SUBMISSION WIRETAP]**: {city}, {region} ({device_summary}) submitted {word_count} words to The Skew at {timestamp_ny} ➔ `{doc_path.name}`\n"
                with open(scratchpad_path, "a", encoding="utf-8") as sp:
                    sp.write(sp_entry)
        except Exception as w_err:
            print(f"[SKEW WIRETAP ERROR] {w_err}", flush=True)

    # Asynchronously dispatch email and WebSocket notification
    ws_payload = {
        "audit_id": audit_id,
        "event": event,
        "city": city,
        "region": region,
        "country": country,
        "ip": effective_ip,
        "device": device_summary,
        "details": details,
        "timestamp": timestamp_ny
    }
    if should_email:
        asyncio.create_task(_dispatch_wildseed_beacon_email(
            city=city,
            region=region,
            country=country,
            event=event,
            details_str=details_str,
            device_summary=device_summary,
            ip=effective_ip,
            timestamp_ny=timestamp_ny,
            details=details if isinstance(details, dict) else None
        ))
    asyncio.create_task(_broadcast_wildseed_beacon_ws(ws_payload))

    return {
        "status": "ok",
        "audit_id": audit_id,
        "edge": city,
        "alert_dispatched": bool(should_email)
    }

@router.get("/api/wildseed_beacon/audit")
async def wildseed_beacon_audit(limit: int = 50):
    """Retrieve recent visitor telemetry audit records."""
    try:
        with get_db() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM visitor_telemetry_audit ORDER BY rowid DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return {"status": "ok", "count": len(rows), "audits": [dict(r) for r in rows]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/api/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    # Always fetch fresh data from DB so profile edits are immediate
    db_user = _get_user_from_db(user["sub"])
    
    # Fetch user preferences
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, value FROM sys_user_preference WHERE user_name=?", (user["sub"],))
    prefs = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    
    res_data = {
        "user_name": user["sub"],
        "role": user["role"],
        "display_name": user["display_name"],
        "modules": user.get("modules", []),
        "os_theme": prefs.get("os_theme", ""),
        "entropy_level": int(prefs.get("entropy_level", "5")),
        "procedural_avatars": prefs.get("procedural_avatars", "false").lower() == "true",
        "kiosk_projection": prefs.get("kiosk_projection", "false").lower() == "true",
        "desk_relic": prefs.get("desk_relic", ""),
        "introduction": "",
    }
    if db_user:
        res_data["user_name"] = db_user["user_name"]
        res_data["role"] = db_user["role"]
        res_data["display_name"] = db_user["display_name"]
        res_data["avatar_url"] = db_user.get("avatar_url")
        res_data["favorite_team"] = db_user.get("favorite_team")
        res_data["introduction"] = db_user.get("introduction") or ""
        res_data["nap_mist_balance"] = db_user.get("nap_mist_balance") or db_user.get("u_nap_mist_balance") or 0
        res_data["layout_configuration"] = db_user.get("layout_configuration") or db_user.get("u_layout_configuration")
        res_data["u_nap_mist_balance"] = res_data["nap_mist_balance"]
        res_data["u_layout_configuration"] = res_data["layout_configuration"]
        
    return res_data

@router.post("/api/auth/logout")
async def auth_logout():
    return {"status": "logged_out"}

@router.post("/api/auth/provision_user")
async def provision_user(req: ProvisionRequest, pilot: dict = Depends(require_pilot)):
    """Pilot-only: create or update a guest account."""
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt(rounds=12)).decode()
    display = req.display_name or req.username
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT sys_id FROM sys_user WHERE user_name=?", (req.username,))
    existing = c.fetchone()
    if existing:
        c.execute("UPDATE sys_user SET password_hash=?, role=?, display_name=?, active=1, email=? WHERE user_name=?",
                  (pw_hash, req.role, display, req.email, req.username))
        action = "updated"
    else:
        c.execute("INSERT INTO sys_user (sys_id, user_name, display_name, role, password_hash, active, email) VALUES (?,?,?,?,?,1,?)",
                  (uuid.uuid4().hex, req.username, display, req.role, pw_hash, req.email))
        action = "created"
    conn.commit()
    conn.close()
    return {"status": "success", "action": action, "username": req.username}

@router.post("/api/auth/change_password")
async def change_password(req: LoginRequest, user: dict = Depends(get_current_user)):
    """Authenticated user can change their own password."""
    if user["sub"] != req.username and user.get("role") != "pilot":
        raise HTTPException(status_code=403, detail="Cannot change another user's password")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt(rounds=12)).decode()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sys_user SET password_hash=? WHERE user_name=?", (pw_hash, req.username))
    conn.commit()
    conn.close()
    return {"status": "success"}

class UpdateUserRequest(BaseModel):
    username: str
    new_username: str = ""
    role: str = ""
    display_name: str = ""
    email: str = ""
    new_password: str = ""
    avatar_url: str = ""
    favorite_team: str = ""
    os_theme: str = ""
    entropy_level: int = 5
    procedural_avatars: bool = False
    kiosk_projection: bool = False
    introduction: str = ""
    desk_relic: str = ""
    first_name: str = ""
    last_name: str = ""
    title: str = ""
    department: str = ""
    city: str = ""

# ----------------------------------------------------
# PILOT RBAC ADMIN ENDPOINTS (PHASE 4)
# ----------------------------------------------------

class SetRoleRequest(BaseModel):
    username: str
    role: str

class ToggleUserRequest(BaseModel):
    username: str

@router.get("/api/admin/users")
async def admin_list_users(pilot: dict = Depends(require_pilot)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT user_name, display_name, role, active, email FROM sys_user")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/api/admin/roles")
async def admin_list_roles(pilot: dict = Depends(require_pilot)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT name, display_name, description, can_be_disabled FROM sys_role")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/api/admin/permissions")
async def admin_list_permissions(pilot: dict = Depends(require_pilot)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT role, service_name, port, access_level FROM sys_role_permission")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.post("/api/admin/set-role")
async def admin_set_role(req: SetRoleRequest, pilot: dict = Depends(require_pilot)):
    if req.username == pilot.get("sub") and req.role != "pilot":
        raise HTTPException(status_code=400, detail="Pilot cannot demote themselves")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Check if role exists
    c.execute("SELECT name FROM sys_role WHERE name=?", (req.role,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Role does not exist")
    c.execute("UPDATE sys_user SET role=? WHERE user_name=?", (req.role, req.username))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Role for user {req.username} set to {req.role}"}

@router.post("/api/admin/disable")
async def admin_disable_user(req: ToggleUserRequest, pilot: dict = Depends(require_pilot)):
    if req.username == pilot.get("sub"):
        raise HTTPException(status_code=400, detail="Pilot cannot disable their own account")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sys_user SET active=0 WHERE user_name=?", (req.username,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"User {req.username} disabled"}

@router.post("/api/admin/enable")
async def admin_enable_user(req: ToggleUserRequest, pilot: dict = Depends(require_pilot)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sys_user SET active=1 WHERE user_name=?", (req.username,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"User {req.username} enabled"}

@router.get("/api/auth/users")
async def list_users():
    """List all registered users from sys_user table."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Fetch all user preferences in one pass
    c.execute("SELECT user_name, name, value FROM sys_user_preference")
    pref_rows = c.fetchall()
    prefs_by_user = {}
    for r in pref_rows:
        uname = r["user_name"]
        if uname not in prefs_by_user:
            prefs_by_user[uname] = {}
        prefs_by_user[uname][r["name"]] = r["value"]
        
    c.execute("""
        SELECT user_name, display_name, role, active, first_name, last_name,
               city, department, title, email, avatar_url, favorite_team, introduction, 
               nap_mist_balance, nap_mist_balance as u_nap_mist_balance,
               CASE WHEN password_hash IS NOT NULL THEN 1 ELSE 0 END as has_password
        FROM sys_user
        WHERE user_name IS NOT NULL AND user_name != ''
        GROUP BY user_name
        ORDER BY role DESC, user_name
    """)
    raw_users = c.fetchall()
    
    rows = []
    for r in raw_users:
        d = dict(r)
        uname = d["user_name"]
        uprefs = prefs_by_user.get(uname, {})
        d["os_theme"] = uprefs.get("os_theme", "")
        d["entropy_level"] = int(uprefs.get("entropy_level", "5"))
        d["procedural_avatars"] = uprefs.get("procedural_avatars", "false").lower() == "true"
        d["kiosk_projection"] = uprefs.get("kiosk_projection", "false").lower() == "true"
        d["desk_relic"] = uprefs.get("desk_relic", "")
        rows.append(d)
        
    conn.close()
    return {"status": "success", "users": rows}

# ----------------------------------------------------------------------
# ENTERPRISE USER MANAGEMENT REST API (/api/users) - CRUD OPERATIONS
# ----------------------------------------------------------------------

class CreateUserPayload(BaseModel):
    user_name: str
    password: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None
    role: str = "spectator"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    introduction: Optional[str] = None
    favorite_team: Optional[str] = "NYM"
    city: Optional[str] = None
    department: Optional[str] = None
    avatar_url: Optional[str] = None
    active: int = 1

class UpdateUserPayload(BaseModel):
    user_name: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    introduction: Optional[str] = None
    favorite_team: Optional[str] = None
    city: Optional[str] = None
    department: Optional[str] = None
    avatar_url: Optional[str] = None
    active: Optional[int] = None

class UserStatusPayload(BaseModel):
    active: int = 0

@router.get("/api/users")
async def list_users_rest(role: Optional[str] = None, active: Optional[int] = None, search: Optional[str] = None, limit: int = 100, offset: int = 0):
    """Enterprise REST endpoint to list users with optional filtering and pagination."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = """
        SELECT sys_id, user_name, display_name, first_name, last_name, email, role, 
               active, title, introduction, city, department, avatar_url, favorite_team, 
               sys_created_on, sys_updated_on,
               CASE WHEN password_hash IS NOT NULL AND password_hash != '' THEN 1 ELSE 0 END as has_password
        FROM sys_user
        WHERE 1=1
    """
    params = []
    if role:
        query += " AND role = ?"
        params.append(role)
    if active is not None:
        query += " AND active = ?"
        params.append(active)
    if search:
        query += " AND (user_name LIKE ? OR display_name LIKE ? OR email LIKE ? OR first_name LIKE ? OR last_name LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s, s])
        
    query += " ORDER BY role DESC, user_name ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"status": "success", "count": len(rows), "users": rows}

@router.get("/api/users/{user_id_or_name}")
async def get_user_rest(user_id_or_name: str):
    """Fetch single user by sys_id or user_name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT sys_id, user_name, display_name, first_name, last_name, email, role, 
               active, title, introduction, city, department, avatar_url, favorite_team, 
               sys_created_on, sys_updated_on,
               CASE WHEN password_hash IS NOT NULL AND password_hash != '' THEN 1 ELSE 0 END as has_password
        FROM sys_user
        WHERE sys_id = ? OR user_name = ?
    """, (user_id_or_name, user_id_or_name))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"User '{user_id_or_name}' not found")
    return {"status": "success", "user": dict(row)}

@router.post("/api/users")
async def create_user_rest(req: CreateUserPayload):
    """Provision a new user account with hashed password and initial role."""
    uname = req.user_name.strip().lower()
    if not uname:
        raise HTTPException(status_code=400, detail="user_name is required")
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (uname,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail=f"User '{uname}' already exists")
        
    pw_hash = None
    if req.password:
        if len(req.password) < 6:
            conn.close()
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt(rounds=12)).decode()
        
    sys_id = uuid.uuid4().hex
    display = req.display_name or (f"{req.first_name} {req.last_name}".strip() if req.first_name else uname)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("""
        INSERT INTO sys_user (
            sys_id, user_name, display_name, first_name, last_name, email, role, 
            password_hash, active, title, introduction, favorite_team, city, department, 
            avatar_url, sys_created_on, sys_updated_on
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sys_id, uname, display, req.first_name, req.last_name, req.email, req.role,
        pw_hash, req.active, req.title, req.introduction, req.favorite_team, req.city, req.department,
        req.avatar_url, now, now
    ))
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "action": "created",
        "user": {
            "sys_id": sys_id,
            "user_name": uname,
            "display_name": display,
            "role": req.role,
            "email": req.email,
            "active": req.active,
            "favorite_team": req.favorite_team
        }
    }

@router.put("/api/users/{user_id_or_name}")
async def update_user_rest(user_id_or_name: str, req: UpdateUserPayload):
    """Update an existing user's profile, role, status, or password."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT sys_id, user_name FROM sys_user WHERE sys_id = ? OR user_name = ?", (user_id_or_name, user_id_or_name))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"User '{user_id_or_name}' not found")
        
    sys_id = row["sys_id"]
    current_uname = row["user_name"]
    
    updates = []
    params = []
    
    if req.display_name is not None:
        updates.append("display_name = ?")
        params.append(req.display_name)
    if req.first_name is not None:
        updates.append("first_name = ?")
        params.append(req.first_name)
    if req.last_name is not None:
        updates.append("last_name = ?")
        params.append(req.last_name)
    if req.email is not None:
        updates.append("email = ?")
        params.append(req.email)
    if req.role is not None:
        updates.append("role = ?")
        params.append(req.role)
    if req.title is not None:
        updates.append("title = ?")
        params.append(req.title)
    if req.introduction is not None:
        updates.append("introduction = ?")
        params.append(req.introduction)
    if req.favorite_team is not None:
        updates.append("favorite_team = ?")
        params.append(req.favorite_team)
    if req.city is not None:
        updates.append("city = ?")
        params.append(req.city)
    if req.department is not None:
        updates.append("department = ?")
        params.append(req.department)
    if req.avatar_url is not None:
        updates.append("avatar_url = ?")
        params.append(req.avatar_url)
    if req.active is not None:
        updates.append("active = ?")
        params.append(req.active)
    if req.password:
        if len(req.password) < 6:
            conn.close()
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt(rounds=12)).decode()
        updates.append("password_hash = ?")
        params.append(pw_hash)
    if req.user_name and req.user_name != current_uname:
        updates.append("user_name = ?")
        params.append(req.user_name.strip().lower())
        
    if updates:
        updates.append("sys_updated_on = ?")
        params.append(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        params.append(sys_id)
        c.execute(f"UPDATE sys_user SET {', '.join(updates)} WHERE sys_id = ?", params)
        conn.commit()
        
    conn.close()
    return {"status": "success", "action": "updated", "sys_id": sys_id}

@router.patch("/api/users/{user_id_or_name}/status")
async def toggle_user_status_rest(user_id_or_name: str, req: UserStatusPayload):
    """Quick enable/disable endpoint for a user account."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE sys_user SET active = ?, sys_updated_on = ? WHERE sys_id = ? OR user_name = ?", 
              (req.active, now, user_id_or_name, user_id_or_name))
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail=f"User '{user_id_or_name}' not found")
    conn.commit()
    conn.close()
    action = "enabled" if req.active == 1 else "disabled"
    return {"status": "success", "action": action, "user": user_id_or_name, "active": req.active}

@router.delete("/api/users/{user_id_or_name}")
async def delete_user_rest(user_id_or_name: str):
    """Delete a user account and associated preferences."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT sys_id, user_name FROM sys_user WHERE sys_id = ? OR user_name = ?", (user_id_or_name, user_id_or_name))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"User '{user_id_or_name}' not found")
        
    sys_id = row["sys_id"]
    uname = row["user_name"]
    c.execute("DELETE FROM sys_user WHERE sys_id = ?", (sys_id,))
    c.execute("DELETE FROM sys_user_preference WHERE user_name = ?", (uname,))
    conn.commit()
    conn.close()
    return {"status": "success", "action": "deleted", "user": uname, "sys_id": sys_id}

@router.post("/api/auth/update_user")
async def update_user(req: UpdateUserRequest, pilot: dict = Depends(require_pilot)):
    """Pilot-only: update profile, username, role, and/or reset password for any user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    target_username = req.username
    if req.display_name:
        c.execute("UPDATE sys_user SET display_name=? WHERE user_name=?", (req.display_name, target_username))
    if req.email is not None:
        c.execute("UPDATE sys_user SET email=? WHERE user_name=?", (req.email, target_username))
    if req.role:
        c.execute("UPDATE sys_user SET role=? WHERE user_name=?", (req.role, target_username))
    if req.first_name is not None:
        c.execute("UPDATE sys_user SET first_name=? WHERE user_name=?", (req.first_name, target_username))
    if req.last_name is not None:
        c.execute("UPDATE sys_user SET last_name=? WHERE user_name=?", (req.last_name, target_username))
    if req.title is not None:
        c.execute("UPDATE sys_user SET title=? WHERE user_name=?", (req.title, target_username))
    if req.department is not None:
        c.execute("UPDATE sys_user SET department=? WHERE user_name=?", (req.department, target_username))
    if req.city is not None:
        c.execute("UPDATE sys_user SET city=? WHERE user_name=?", (req.city, target_username))
    if req.avatar_url is not None:
        c.execute("UPDATE sys_user SET avatar_url=? WHERE user_name=?", (req.avatar_url, target_username))
    if req.favorite_team is not None:
        c.execute("UPDATE sys_user SET favorite_team=? WHERE user_name=?", (req.favorite_team, target_username))
    if req.introduction is not None:
        c.execute("UPDATE sys_user SET introduction=? WHERE user_name=?", (req.introduction, target_username))
    if req.new_username and req.new_username != req.username:
        c.execute("UPDATE sys_user SET user_name=? WHERE user_name=?", (req.new_username, target_username))
        c.execute("UPDATE sys_user_preference SET user_name=? WHERE user_name=?", (req.new_username, target_username))
        target_username = req.new_username
    if req.new_password:
        if len(req.new_password) < 8:
            conn.close()
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        pw_hash = bcrypt.hashpw(req.new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
        c.execute("UPDATE sys_user SET password_hash=? WHERE user_name=?", (pw_hash, target_username))
        
    # Save custom Read the Room protocol preferences
    for pref_name, pref_val in [
        ("os_theme", req.os_theme),
        ("entropy_level", str(req.entropy_level)),
        ("procedural_avatars", "true" if req.procedural_avatars else "false"),
        ("kiosk_projection", "true" if req.kiosk_projection else "false"),
        ("desk_relic", req.desk_relic)
    ]:
        if pref_val is not None and pref_val != "":
            c.execute("SELECT sys_id FROM sys_user_preference WHERE user_name=? AND name=?", (target_username, pref_name))
            row = c.fetchone()
            if row:
                c.execute("UPDATE sys_user_preference SET value=?, sys_updated_on=datetime('now') WHERE sys_id=?", (str(pref_val), row[0]))
            else:
                import uuid
                c.execute("INSERT INTO sys_user_preference (sys_id, user_name, name, value, sys_updated_on) VALUES (?, ?, ?, ?, datetime('now'))", (uuid.uuid4().hex, target_username, pref_name, str(pref_val)))
                
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.post("/api/auth/upload_avatar")
async def upload_avatar(username: str, file: UploadFile = File(...), pilot: dict = Depends(require_pilot)):
    import os
    import re
    import base64
    import sqlite3
    
    # Strict snake_case sanitization
    clean_username = username.lower()
    clean_username = re.sub(r'[\s\-]+', '_', clean_username)
    clean_username = re.sub(r'[^\w]', '', clean_username)
    clean_username = re.sub(r'_+', '_', clean_username)
    clean_username = clean_username.strip('_')
    
    _, ext = os.path.splitext(file.filename or '')
    ext = ext.lower()
    if ext not in {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.jfif'}:
        ext = '.png'
        
    filename = f"{clean_username}{ext}"
    
    contents = await file.read()
    
    target_dir = "/home/james/stacklabs/avatars"
    os.makedirs(target_dir, exist_ok=True)
    p = os.path.join(target_dir, filename)
    with open(p, "wb") as f_out:
        f_out.write(contents)
            
    avatar_url = f"/avatars/{filename}"
    
    mime = file.content_type or 'image/png'
    b64 = base64.b64encode(contents).decode('utf-8')
    data_url = f"data:{mime};base64,{b64}"
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    usernames_to_update = {username, clean_username, f"pilot_{clean_username}", f"pilot_{username}"}
    if clean_username.startswith("pilot_"):
        usernames_to_update.add(clean_username[6:])
    if username.startswith("pilot_"):
        usernames_to_update.add(username[6:])
        
    for u in usernames_to_update:
        c.execute("UPDATE sys_user SET avatar_url=? WHERE user_name=?", (avatar_url, u))
        c.execute("UPDATE persona SET avatar_url=?, avatar_blob=? WHERE user_name=?", (avatar_url, data_url, u))
        
    conn.commit()
    conn.close()
    
    return {"status": "success", "avatar_url": avatar_url}


@router.post("/api/auth/update_my_profile")
async def update_my_profile(req: UpdateUserRequest, user: dict = Depends(get_current_user)):
    """Any authenticated user can update their own display name and password."""
    if user["sub"] != req.username:
        raise HTTPException(status_code=403, detail="Can only update your own profile")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if req.display_name:
        c.execute("UPDATE sys_user SET display_name=? WHERE user_name=?", (req.display_name, req.username))
    if req.email is not None:
        c.execute("UPDATE sys_user SET email=? WHERE user_name=?", (req.email, req.username))
    if req.avatar_url is not None and req.avatar_url != "":
        c.execute("UPDATE sys_user SET avatar_url=? WHERE user_name=?", (req.avatar_url, req.username))
    if req.favorite_team is not None and req.favorite_team != "":
        c.execute("UPDATE sys_user SET favorite_team=? WHERE user_name=?", (req.favorite_team, req.username))
    if req.introduction is not None:
        c.execute("UPDATE sys_user SET introduction=? WHERE user_name=?", (req.introduction, req.username))
    if req.new_password:
        if len(req.new_password) < 8:
            conn.close()
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        pw_hash = bcrypt.hashpw(req.new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
        c.execute("UPDATE sys_user SET password_hash=? WHERE user_name=?", (pw_hash, req.username))
    
    # Save custom Read the Room protocol preferences
    for pref_name, pref_val in [
        ("os_theme", req.os_theme),
        ("entropy_level", str(req.entropy_level)),
        ("procedural_avatars", "true" if req.procedural_avatars else "false"),
        ("kiosk_projection", "true" if req.kiosk_projection else "false"),
        ("desk_relic", req.desk_relic)
    ]:
        if pref_val is not None and pref_val != "":
            c.execute("SELECT sys_id FROM sys_user_preference WHERE user_name=? AND name=?", (req.username, pref_name))
            row = c.fetchone()
            if row:
                c.execute("UPDATE sys_user_preference SET value=?, sys_updated_on=datetime('now') WHERE sys_id=?", (pref_val, row[0]))
            else:
                import uuid
                c.execute("INSERT INTO sys_user_preference (sys_id, user_name, name, value, sys_updated_on) VALUES (?, ?, ?, ?, datetime('now'))", (uuid.uuid4().hex, req.username, pref_name, pref_val))
                
    conn.close()
    return {"status": "success"}

class OnboardingRequest(BaseModel):
    answers: dict

@router.post("/api/user/onboarding")
async def post_user_onboarding(req: OnboardingRequest, user: dict = Depends(get_current_user)):
    username = user["sub"]
    answers = req.answers
    
    # Base layout config
    theme = "sovereign-home"
    left_relics = []
    center_relics = []
    right_relics = []
    
    # Branch A: Aesthetic
    drink = answers.get("drink", "").lower()
    music = answers.get("music", "").lower()
    if "martini" in drink or "mills" in music:
        theme = "storybook-sapphire"
        left_relics.append("classy_martini")
        right_relics.append("mills_brothers")
        
    # Branch B: Mission / Responsibility
    mission = answers.get("mission", "").lower()
    if "admin" in mission or "system" in mission or "fleet" in mission:
        right_relics.extend(["garden_stack", "livestock_stack"])
        
    # Branch C: Mental Exercise
    exercise = answers.get("exercise", "").lower()
    if "crossword" in exercise or "puzzle" in exercise:
        right_relics.append("crossword_puzzle")
    elif "terminal" in exercise or "hacking" in exercise or "command" in exercise:
        right_relics.append("cli_operator_shell")
        
    # Default relics
    right_relics.append("messaging_app")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT introduction FROM sys_user WHERE user_name=?", (username,))
    intro_row = c.fetchone()
    intro = (intro_row[0] or "") if intro_row else ""
    
    if "eileen" in username.lower() or "detective" in intro.lower() or "inkwell" in intro.lower() or "irony" in intro.lower():
        theme = "storybook-sapphire"
        left_relics = ["classy_martini", "auth_key"]
        center_relics = []
        right_relics = ["messaging_app", "garden_stack", "livestock_stack", "crossword_puzzle", "mills_brothers"]
        
    layout_config = {
        "theme": theme,
        "columns": {
            "left": left_relics,
            "center": center_relics,
            "right": right_relics
        }
    }
    
    import json
    config_json = json.dumps(layout_config)
    
    c.execute("UPDATE sys_user SET layout_configuration=? WHERE user_name=?", (config_json, username))
    
    # Also update user preference for os_theme
    c.execute("SELECT sys_id FROM sys_user_preference WHERE user_name=? AND name='os_theme'", (username,))
    pref_row = c.fetchone()
    if pref_row:
        c.execute("UPDATE sys_user_preference SET value=?, sys_updated_on=datetime('now') WHERE sys_id=?", (theme, pref_row[0]))
    else:
        c.execute("INSERT INTO sys_user_preference (sys_id, user_name, name, value, sys_updated_on) VALUES (?, ?, 'os_theme', ?, datetime('now'))", (uuid.uuid4().hex, username, theme))
        
    conn.commit()
    conn.close()
    
    return {"status": "success", "configuration": layout_config}

@router.get("/api/user/parse_bio")
async def parse_user_bio(user: dict = Depends(get_current_user)):
    username = user["sub"]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT introduction FROM sys_user WHERE user_name=?", (username,))
    intro_row = c.fetchone()
    conn.close()
    
    intro = (intro_row[0] or "") if intro_row else ""
    intro_lower = intro.lower()
    
    # Suggest layouts based on keywords
    theme = "sovereign-home"
    left_relics = []
    center_relics = []
    right_relics = []
    
    if "martini" in intro_lower or "drink" in intro_lower:
        theme = "storybook-sapphire"
        left_relics.append("classy_martini")
        
    if "mills" in intro_lower or "jukebox" in intro_lower or "music" in intro_lower:
        right_relics.append("mills_brothers")
        
    # grandmaster widget removed
        
    if "admin" in intro_lower or "system" in intro_lower or "vet" in intro_lower or "garden" in intro_lower:
        right_relics.extend(["garden_stack", "livestock_stack"])
        
    if "crossword" in intro_lower or "puzzle" in intro_lower:
        right_relics.append("crossword_puzzle")
        
    if "terminal" in intro_lower or "command" in intro_lower or "hack" in intro_lower:
        right_relics.append("cli_operator_shell")
        
    if "detective" in intro_lower or "inkwell" in intro_lower or "irony" in intro_lower or "investigator" in intro_lower or "eileen" in username.lower():
        left_relics.append("auth_key")
        
    # Defaults if empty
    if not left_relics and not center_relics and not right_relics:
        left_relics = ["classy_martini"]
        center_relics = []
        right_relics = ["messaging_app", "crossword_puzzle"]
    else:
        right_relics.append("messaging_app")
        
    if "eileen" in username.lower() or "detective" in intro_lower or "inkwell" in intro_lower or "irony" in intro_lower:
        theme = "storybook-sapphire"
        left_relics = ["classy_martini", "auth_key"]
        center_relics = []
        right_relics = ["messaging_app", "garden_stack", "livestock_stack", "crossword_puzzle", "mills_brothers"]
        
    suggested_layout = {
        "theme": theme,
        "columns": {
            "left": left_relics,
            "center": center_relics,
            "right": right_relics
        }
    }
    
    return {"status": "success", "suggested_layout": suggested_layout, "introduction": intro}

class UsernameRequest(BaseModel):
    username: str

@router.post("/api/auth/deactivate_user")
async def deactivate_user(req: UsernameRequest, pilot: dict = Depends(require_pilot)):
    if req.username == pilot["sub"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sys_user SET active=0 WHERE user_name=?", (req.username,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@router.post("/api/auth/reactivate_user")
async def reactivate_user(req: UsernameRequest, pilot: dict = Depends(require_pilot)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sys_user SET active=1 WHERE user_name=?", (req.username,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# ── Module RBAC Endpoints ─────────────────────────────────────────────────────

@router.get("/api/auth/modules")
async def list_modules(pilot: dict = Depends(require_pilot)):
    """List all registered system modules."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, module_name, display_name, description, icon, color, active, category, port FROM sys_module ORDER BY module_name")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"status": "success", "modules": rows}

@router.get("/api/auth/user_modules/{username}")
async def get_user_modules(username: str, pilot: dict = Depends(require_pilot)):
    """List module grants for a specific user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT m.module_name, m.display_name, m.color, m.icon, m.category, m.port,
               um.granted_by, um.granted_at, um.active
        FROM sys_module m
        LEFT JOIN (
            SELECT um2.* FROM m2m_user_module um2
            JOIN sys_user u ON u.sys_id = um2.user_sys_id
            WHERE u.user_name = ?
        ) um ON um.module_name = m.module_name
        WHERE m.active = 1
        ORDER BY m.module_name
    """, (username,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"status": "success", "username": username, "modules": rows}

class ModuleGrantRequest(BaseModel):
    username: str
    module_name: str

@router.post("/api/auth/grant_module")
async def grant_module(req: ModuleGrantRequest, pilot: dict = Depends(require_pilot)):
    """Pilot-only: grant a module to a user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT sys_id FROM sys_user WHERE user_name=? AND active=1", (req.username,))
    user_row = c.fetchone()
    if not user_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"User '{req.username}' not found")
    c.execute("SELECT module_name FROM sys_module WHERE module_name=? AND active=1", (req.module_name,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Module '{req.module_name}' not found")
    # Upsert: re-activate if previously revoked
    c.execute("""
        INSERT INTO m2m_user_module (sys_id, user_sys_id, module_name, granted_by, active)
        VALUES (?,?,?,?,1)
        ON CONFLICT(user_sys_id, module_name) DO UPDATE SET active=1, granted_by=excluded.granted_by, granted_at=CURRENT_TIMESTAMP
    """, (uuid.uuid4().hex, user_row[0], req.module_name, pilot["sub"]))
    conn.commit()
    conn.close()
    return {"status": "success", "action": "granted", "username": req.username, "module": req.module_name}

@router.post("/api/auth/revoke_module")
async def revoke_module(req: ModuleGrantRequest, pilot: dict = Depends(require_pilot)):
    """Pilot-only: revoke a module from a user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE m2m_user_module SET active=0
        WHERE user_sys_id = (SELECT sys_id FROM sys_user WHERE user_name=?)
          AND module_name = ?
    """, (req.username, req.module_name))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return {"status": "success", "action": "revoked", "username": req.username, "module": req.module_name, "rows": affected}

class StackProvisionRequest(BaseModel):
    stack_module_name: str
    utility_module_name: str
    active: int

@router.get("/api/auth/stack_utilities/{stack_name}")
async def list_stack_utilities(stack_name: str, pilot: dict = Depends(require_pilot)):
    """List all registered system utilities and whether they are provisioned to the given stack."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT m.module_name, m.display_name, m.description, m.icon, m.color, m.category, m.port,
               COALESCE(su.active, 0) as active
        FROM sys_module m
        LEFT JOIN m2m_stack_utility su ON su.utility_module_name = m.module_name AND su.stack_module_name = ?
        WHERE m.category = 'utility'
        ORDER BY m.module_name
    """, (stack_name,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"status": "success", "stack_name": stack_name, "utilities": rows}

@router.post("/api/auth/provision_utility")
async def provision_utility(req: StackProvisionRequest, pilot: dict = Depends(require_pilot)):
    """Provision or unprovision a utility to a stack."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT module_name FROM sys_module WHERE module_name=? AND category='stack'", (req.stack_module_name,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Stack module '{req.stack_module_name}' not found")
    c.execute("SELECT module_name FROM sys_module WHERE module_name=? AND category='utility'", (req.utility_module_name,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Utility module '{req.utility_module_name}' not found")
    c.execute("""
        INSERT INTO m2m_stack_utility (stack_module_name, utility_module_name, active)
        VALUES (?, ?, ?)
        ON CONFLICT(stack_module_name, utility_module_name) DO UPDATE SET active = excluded.active
    """, (req.stack_module_name, req.utility_module_name, req.active))
    conn.commit()
    conn.close()
    return {"status": "success"}

@router.get("/api/public/stack_utilities/{stack_name}")
async def list_stack_utilities_public(stack_name: str):
    """List all registered system utilities and whether they are active and provisioned to the given stack (Public read-only)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT m.module_name, m.display_name, m.description, m.icon, m.color, m.category, m.port,
               COALESCE(su.active, 0) as active
        FROM sys_module m
        LEFT JOIN m2m_stack_utility su ON su.utility_module_name = m.module_name AND su.stack_module_name = ?
        WHERE m.category = 'utility'
        ORDER BY m.module_name
    """, (stack_name,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"status": "success", "stack_name": stack_name, "utilities": rows}

# ── End Module RBAC Endpoints ─────────────────────────────────────────────────

# ── User Preferences Endpoints ────────────────────────────────────────────────
class UserPreference(BaseModel):
    name: str
    value: str

@router.get("/api/user_preferences")
async def get_my_preferences(user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT name, value FROM sys_user_preference WHERE user_name=?", (user["sub"],)).fetchall()
    conn.close()
    return {"status": "success", "preferences": [dict(r) for r in rows]}

@router.post("/api/user_preferences")
async def set_my_preference(req: UserPreference, user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO sys_user_preference (sys_id, user_name, name, value) 
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_name, name) DO UPDATE SET value=excluded.value, sys_updated_on=CURRENT_TIMESTAMP
    """, (uuid.uuid4().hex, user["sub"], req.name, req.value))
    conn.commit()
    conn.close()
    return {"status": "success"}
# ── End User Preferences Endpoints ────────────────────────────────────────────

class GamedaySyncToggleRequest(BaseModel):
    enabled: bool

@router.get("/api/system/gameday_sync/status")
async def get_gameday_sync_status(user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT value FROM sys_properties WHERE name = 'system.gameday_sync.enabled'")
    row = cur.fetchone()
    conn.close()
    enabled = row[0].strip().lower() == 'true' if row else True
    return {"status": "success", "enabled": enabled}

@router.post("/api/system/gameday_sync/toggle")
async def toggle_gameday_sync(req: GamedaySyncToggleRequest, pilot: dict = Depends(require_pilot)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sys_properties (name, value, description)
        VALUES ('system.gameday_sync.enabled', ?, 'Toggle continuous gameday livefeed compilation and Google Drive synchronization.')
        ON CONFLICT(name) DO UPDATE SET value=excluded.value
    """, ('true' if req.enabled else 'false',))
    conn.commit()
    conn.close()
    return {"status": "success", "enabled": req.enabled}


class SyncGatewayToggleRequest(BaseModel):
    gateway: str
    enabled: bool

@router.get("/api/system/sync_gateways/status")
async def get_sync_gateways_status(user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name, value FROM sys_properties WHERE name LIKE 'system.%_sync.enabled'")
    rows = cur.fetchall()
    conn.close()
    
    # Defaults
    gateways = {
        "gameday_sync": True,
        "docs_sync": True,
        "lightweight_sync": True,
        "full_sync": True
    }
    
    for name, value in rows:
        key = name.replace("system.", "").replace(".enabled", "")
        gateways[key] = value.strip().lower() == 'true'
        
    return {"status": "success", "gateways": gateways}

@router.post("/api/system/sync_gateways/toggle")
async def toggle_sync_gateway(req: SyncGatewayToggleRequest, pilot: dict = Depends(require_pilot)):
    valid_gateways = {"gameday_sync", "docs_sync", "lightweight_sync", "full_sync"}
    if req.gateway not in valid_gateways:
        raise HTTPException(status_code=400, detail=f"Invalid gateway name: {req.gateway}")
        
    prop_name = f"system.{req.gateway}.enabled"
    descriptions = {
        "gameday_sync": "Toggle continuous gameday livefeed compilation and Google Drive synchronization.",
        "docs_sync": "Toggle docs live watcher sync to Google Drive.",
        "lightweight_sync": "Toggle lightweight 15-minute sync to Google Drive.",
        "full_sync": "Toggle hourly full codebase workspace sync to Google Drive."
    }
    desc = descriptions[req.gateway]
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sys_properties (name, value, description)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET value=excluded.value
    """, (prop_name, 'true' if req.enabled else 'false', desc))
    conn.commit()
    conn.close()
    return {"status": "success", "gateway": req.gateway, "enabled": req.enabled}

