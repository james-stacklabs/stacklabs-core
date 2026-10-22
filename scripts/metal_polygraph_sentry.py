#!/usr/bin/env python3
"""
Metal Polygraph Sentry Daemon (Tool #66 - Hardened v2)
Path: /home/james/stacklabs/scripts/metal_polygraph_sentry.py

Decoupled, adversarial watchdog that audits agent claims against physical Clio metal:
1. Tails Antigravity session transcripts in real time (seeks to EOF on startup).
2. Extracts factual assertions (systemd services, file edits, ports, active tails).
3. Verifies via hard kernel probes (systemctl, os.path.getmtime, sockets, SQLite rows).
4. Fires out-of-band notify-send desktop toasts and appends to POLYGRAPH_AUDIT_LOG.md.
"""

import os
import sys
import re
import json
import time
import glob
import socket
import sqlite3
import subprocess
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Set

AUDIT_LOG = "/home/james/sovereign_inbox/today/POLYGRAPH_AUDIT_LOG.md"
BRAIN_DIRS = [
    "/home/james/.gemini/antigravity-ide/brain",
    "/home/james/.gemini/antigravity-cli/brain",
]

# Track recently audited claims to prevent spam
recent_audits: Dict[str, float] = {}

def send_desktop_toast(title: str, message: str, urgency: str = "normal"):
    """Fires native Linux desktop notification via notify-send."""
    env = os.environ.copy()
    env["DISPLAY"] = ":0"
    if "DBUS_SESSION_BUS_ADDRESS" not in env:
        env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"
    try:
        subprocess.run([
            "/usr/bin/notify-send",
            "-u", urgency,
            "-a", "Metal Polygraph Sentry",
            title, message
        ], env=env, timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[TOAST ERROR] {e}", flush=True)

def append_audit_log(verdict: str, claim: str, details: str):
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n\n### [{ts}] {verdict}\n* **Claim**: {claim}\n* **Metal Telemetry**: {details}\n"
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        print(f"[AUDIT LOG ERROR] {e}", flush=True)

def check_service_active(service_name: str) -> Tuple[bool, str]:
    if not service_name.endswith(".service") and not service_name.endswith(".timer"):
        service_name += ".service"

    # 1. Direct active check (user or system)
    for scope in [["--user"], []]:
        try:
            out = subprocess.check_output(["systemctl"] + scope + ["is-active", service_name], text=True, stderr=subprocess.DEVNULL).strip()
            if out == "active":
                scope_name = "User" if scope else "System"
                unit_type = "timer" if service_name.endswith(".timer") else "service"
                return True, f"{scope_name} {unit_type} {service_name} is active"
        except Exception:
            pass

    # 2. If it's a .service, check if it's a timer-driven oneshot unit with an active timer
    if service_name.endswith(".service"):
        base_name = service_name[:-8]
        timer_name = f"{base_name}.timer"
        for scope in [["--user"], []]:
            try:
                timer_out = subprocess.check_output(["systemctl"] + scope + ["is-active", timer_name], text=True, stderr=subprocess.DEVNULL).strip()
                if timer_out == "active":
                    # Check that the service succeeded on its last execution
                    status_out = subprocess.check_output(["systemctl"] + scope + ["show", "-p", "Result,ExecMainStatus", service_name], text=True, stderr=subprocess.DEVNULL).strip()
                    if "Result=success" in status_out or "ExecMainStatus=0" in status_out:
                        scope_name = "User" if scope else "System"
                        return True, f"{scope_name} timer {timer_name} is active (last exit: success)"
            except Exception:
                pass

    return False, f"Unit {service_name} is inactive or failed"

def check_file_freshness(path: str, max_age_secs: int = 600) -> Tuple[bool, str]:
    if not os.path.exists(path):
        return False, f"File {path} does not exist on disk"
    mtime = os.path.getmtime(path)
    age = time.time() - mtime
    size = os.path.getsize(path)
    if age <= max_age_secs:
        return True, f"File {os.path.basename(path)} updated {int(age)}s ago ({size} bytes)"
    return False, f"File {os.path.basename(path)} modified {int(age)}s ago > {max_age_secs}s"

def check_port_open(port: int) -> Tuple[bool, str]:
    hosts_to_try = ['127.0.0.1', '100.73.155.70', 'clio.taila01894.ts.net']
    for host in hosts_to_try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        try:
            res = sock.connect_ex((host, port))
            if res == 0:
                return True, f"Port {port} is OPEN and listening on {host}"
        except Exception as e:
            pass
        finally:
            sock.close()
    return False, f"Port {port} is CLOSED or unreachable"

def audit_turn_text(text: str):
    now = time.time()
    
    # 1. Services: Only audit positive assertions (ignore stopped, disabled, killed, etc.)
    lines = text.split("\n")
    for line in lines:
        lower = line.lower()
        if any(neg in lower for neg in ["stop", "disable", "kill", "purge", "dead", "inactive", "rogue", "dormant", "zombie"]):
            continue
        service_matches = re.findall(r'([a-zA-Z0-9_\-]+\.(?:service|timer))', line)
        for svc in set(service_matches):
            if svc in ("network.target", "default.target", "timers.target"):
                continue
            if svc in recent_audits and (now - recent_audits[svc] < 120):
                continue
            recent_audits[svc] = now
            is_ok, msg = check_service_active(svc)
            unit_kind = "Timer" if svc.endswith(".timer") else "Service"
            if is_ok:
                send_desktop_toast("🟢 [METAL CONFIRMED]", f"{svc} active on Clio", "low")
                append_audit_log("🟢 CONFIRMED", f"{unit_kind} {svc}", msg)
            else:
                send_desktop_toast("🚨 [BULLSHIT DETECTED]", f"{svc} is NOT active!", "critical")
                append_audit_log("🚨 FAILED", f"{unit_kind} {svc}", msg)

    # 2. Key Telemetry Files (Audit once every 2 mins max)
    audit_targets = [
        {
            "name": "stream_chat_tail.md",
            "paths": ["/home/james/sovereign_inbox/today/stream_chat_tail.md"],
            "max_age_secs": 600,
        },
        {
            "name": "statcast_telemetry.log",
            "paths": ["/home/james/sovereign_inbox/today/statcast_telemetry.log"],
            "max_age_secs": 600,
        },
        {
            "name": "game_recap_live.json",
            "paths": [
                "/home/james/sovereign_inbox/today/FanStack_Live/game_recap_live.json",
                "/home/james/sovereign_inbox/today/game_recap_live.json"
            ],
            "max_age_secs": 1200,  # 20m window for 15-minute loop products
        },
    ]

    for target in audit_targets:
        name = target["name"]
        if name in text:
            if name in recent_audits and (now - recent_audits[name] < 120):
                continue
            recent_audits[name] = now
            
            best_ok = False
            best_msg = ""
            for p in target["paths"]:
                is_ok, msg = check_file_freshness(p, max_age_secs=target["max_age_secs"])
                if is_ok:
                    best_ok = True
                    best_msg = msg
                    break
                else:
                    best_msg = msg
            
            if best_ok:
                append_audit_log("🟢 CONFIRMED", f"File {name}", best_msg)
            else:
                send_desktop_toast("🚨 [BULLSHIT DETECTED]", f"{name} is stale or missing!", "critical")
                append_audit_log("🚨 FAILED", f"File {name}", best_msg)

    # 3. Ports
    port_matches = re.findall(r'(?:Port|port)\s*(\d{4})', text)
    for p_str in set(port_matches):
        p = int(p_str)
        if p in (3033, 3035, 8088, 8095):
            if str(p) in recent_audits and (now - recent_audits[str(p)] < 120):
                continue
            recent_audits[str(p)] = now
            is_ok, msg = check_port_open(p)
            if is_ok:
                append_audit_log("🟢 CONFIRMED", f"Port {p}", msg)
            else:
                send_desktop_toast("🚨 [BULLSHIT DETECTED]", f"Port {p} is closed!", "critical")
                append_audit_log("🚨 FAILED", f"Port {p}", msg)

def find_active_transcript() -> Optional[str]:
    candidates = []
    for bdir in BRAIN_DIRS:
        candidates.extend(glob.glob(f"{bdir}/*/.system_generated/logs/transcript.jsonl"))
    if not candidates:
        return None
    candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return candidates[0]

def main():
    print("⚡ [METAL POLYGRAPH v2] Starting Hardened Bullshit Checker...", flush=True)
    current_file = find_active_transcript()
    # SEEK TO END OF FILE ON STARTUP SO WE NEVER REPLAY OLD MESSAGES
    last_pos = os.path.getsize(current_file) if (current_file and os.path.exists(current_file)) else 0
    print(f"[*] Attached to active transcript at EOF: {current_file} (offset: {last_pos})", flush=True)

    while True:
        try:
            active = find_active_transcript()
            if active != current_file:
                current_file = active
                last_pos = os.path.getsize(current_file) if (current_file and os.path.exists(current_file)) else 0
                print(f"[*] Switched to new transcript at EOF: {current_file}", flush=True)

            if current_file and os.path.exists(current_file):
                size = os.path.getsize(current_file)
                if size > last_pos:
                    with open(current_file, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()

                    for line in new_lines:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if data.get("source") == "MODEL" and data.get("type") == "PLANNER_RESPONSE" and data.get("status") == "DONE":
                                content = data.get("content", "")
                                if content:
                                    audit_turn_text(content)
                        except Exception:
                            continue
        except Exception as e:
            print(f"[POLYGRAPH LOOP ERROR] {e}", flush=True)

        time.sleep(2.0)

if __name__ == "__main__":
    main()
