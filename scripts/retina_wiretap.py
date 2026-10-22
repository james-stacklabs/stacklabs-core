#!/usr/bin/env python3
"""
StackLabs Platform: Retina Wiretap & Allocator Telemetry Sentry
Path: /home/james/stacklabs/scripts/retina_wiretap.py
Author: James Carroll (Lead Systems Architect)

Dual-layer telemetry sentry for retina.stacklabsllc.com (Port 3028):
1. Intercepts raw HTTP server requests (page hits, optical stream connects).
2. Receives client-side beacon telemetry (pill clicks, scenario triggers, heartbeats).
3. Appends structured JSON lines to /home/james/stacklabs/logs/retina_wiretap.log.
4. Dispatches real-time push alerts to Pilot via scripts.pilot_notifier.
Target: Clio (100.96.77.20) | Python 3.12 (.venv)
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

REPO_ROOT = Path("/home/james/stacklabs")
LOG_FILE = REPO_ROOT / "logs" / "retina_wiretap.log"

PAWEL_IP = "98.185.224.114"

# Attempt to load centralized pilot notifier
try:
    from scripts.pilot_notifier import dispatch_pilot_alert
except ImportError:
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from scripts.pilot_notifier import dispatch_pilot_alert
    except Exception:
        def dispatch_pilot_alert(*args, **kwargs):
            return False


def get_client_ip(headers, client_address) -> str:
    """Extract public client IP prioritizing Cloudflare headers."""
    cf_ip = headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()
    
    xff = headers.get("x-forwarded-for")
    if xff and xff.strip():
        return xff.split(",")[0].strip()
        
    return client_address[0] if client_address else "unknown"


def parse_device_type(user_agent: str) -> str:
    """Classify device category from user agent."""
    ua = user_agent or ""
    if "iPhone" in ua:
        return "iPhone"
    if "iPad" in ua:
        return "iPad"
    if "Android" in ua:
        return "Android"
    if "Macintosh" in ua or "Mac OS" in ua:
        return "Mac Desktop"
    if "Windows" in ua:
        return "Windows Desktop"
    if "Linux" in ua and "Android" not in ua:
        return "Linux Desktop"
    return "Other"


def is_internal_request(ip: str, user_agent: str) -> bool:
    """Detect local health probes, curl sweeps, and loopback hits."""
    if ip in ("127.0.0.1", "::1", "localhost", "unknown"):
        return True
    if ip.startswith("192.168.") or ip.startswith("100.") or ip.startswith("10."):
        return True
    ua = (user_agent or "").lower()
    if "curl" in ua or "headlesschrome" in ua or "healthcheck" in ua:
        return True
    return False


def log_wiretap_event(
    source: str,
    event: str,
    ip: str,
    country: str,
    user_agent: str,
    data: Optional[Dict[str, Any]] = None,
    url: str = ""
):
    """
    Append an immutable structured JSON entry to retina_wiretap.log
    and trigger asynchronous Pilot notification for external visits.
    """
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    device = parse_device_type(user_agent)
    internal = is_internal_request(ip, user_agent)
    is_pawel = (ip == PAWEL_IP)
    counterparty = "PAWEL_RUDNICKI" if is_pawel else ("INTERNAL" if internal else "EXTERNAL_VISITOR")

    entry = {
        "timestamp": now_iso,
        "source": source,
        "event": event,
        "ip": ip,
        "country": country or "unknown",
        "device": device,
        "userAgent": user_agent,
        "is_internal": internal,
        "is_pawel": is_pawel,
        "counterparty": counterparty,
        "url": url,
        "data": data or {}
    }

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        sys.stderr.write(f"[RETINA_WIRETAP] Write error: {e}\n")

    # Dispatch Pilot notification in background thread (suppressed for internal & routine heartbeats)
    if not internal and event != "HEARTBEAT":
        threading.Thread(
            target=_dispatch_async_alert,
            args=(event, ip, country, device, is_pawel, data),
            daemon=True
        ).start()


def _dispatch_async_alert(event: str, ip: str, country: str, device: str, is_pawel: bool, data: Optional[Dict[str, Any]]):
    """Background notification worker to avoid delaying HTTP requests."""
    try:
        data_dict = data or {}
        quad = data_dict.get("quadrant") or data_dict.get("label") or ""
        action = data_dict.get("action") or data_dict.get("scenario") or ""
        
        detail_parts = [f"Device: {device}", f"IP: {ip} ({country})"]
        if quad:
            detail_parts.append(f"Pillar: {quad}")
        if action:
            detail_parts.append(f"Action: {action}")
            
        body = " | ".join(detail_parts)

        if is_pawel:
            title = f"⭐ [PAWEL RUDNICKI] Active on Retina HUD // {event}"
            priority = "urgent"
            tags = "star,eyes,chart_with_upwards_trend"
        else:
            title = f"👀 [RETINA WIRETAP] External Visitor // {event}"
            priority = "high"
            tags = "eyes,bell"

        dispatch_pilot_alert(
            title=title,
            body=body,
            priority=priority,
            tags=tags,
            click_url="https://retina.stacklabsllc.com"
        )
    except Exception as err:
        sys.stderr.write(f"[RETINA_WIRETAP] Alert dispatch failed: {err}\n")


def handle_wiretap_beacon(handler) -> bool:
    """Process incoming client-side beacon via POST /api/wiretap."""
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
    
    try:
        payload = json.loads(body)
    except Exception:
        payload = {"event": "RAW_BEACON", "raw": body}

    client_ip = get_client_ip(handler.headers, handler.client_address)
    country = handler.headers.get("cf-ipcountry", "unknown")
    user_agent = handler.headers.get("user-agent", "unknown")

    log_wiretap_event(
        source="CLIENT_BEACON",
        event=payload.get("event", "UNKNOWN"),
        ip=client_ip,
        country=country,
        user_agent=user_agent,
        data=payload,
        url=payload.get("url", "")
    )

    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps({"status": "ok", "logged": True}).encode("utf-8"))
    return True


def intercept_server_request(handler):
    """Log direct page requests and optical video stream accesses."""
    url = handler.path or ""
    
    # Intercept document root, HTML, and MJPEG video stream requests
    if url in ("/", "/index.html") or url.startswith("/?") or url.startswith("/stream/c120"):
        client_ip = get_client_ip(handler.headers, handler.client_address)
        country = handler.headers.get("cf-ipcountry", "unknown")
        user_agent = handler.headers.get("user-agent", "unknown")
        
        event = "STREAM_CONNECT" if url.startswith("/stream/c120") else "PAGE_REQUEST"
        
        log_wiretap_event(
            source="SERVER_REQUEST",
            event=event,
            ip=client_ip,
            country=country,
            user_agent=user_agent,
            data={"method": handler.command, "path": url},
            url=url
        )
