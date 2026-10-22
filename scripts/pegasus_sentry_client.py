#!/usr/bin/env python3
"""
Sovereign OS — Pegasus Visual Sentry Client SDK
Path: /home/james/stacklabs/scripts/pegasus_sentry_client.py

Triggers Pegasus (100.96.77.20) over Tailscale to execute headless Playwright UAT,
validate KI-095 viewport compliance, capture screenshots, and pull them back to Clio.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime

PEGASUS_IP = "100.96.77.20"
PEGASUS_USER = "james"
CLIO_IP = "100.73.155.70"
REMOTE_VENV = "/home/james/sovereign_sentry/.venv/bin/python3"
REMOTE_SCRIPT = "/home/james/sovereign_sentry/pegasus_sentry.py"

ROOM_URLS = {
    "sentinel": "https://clio.taila01894.ts.net:3038/",
    "kanban": "https://clio.taila01894.ts.net:3016/?domain=ROOT&room=kanban",
    "cockpit": "https://clio.taila01894.ts.net:3016/?domain=ROOT&room=cockpit",
    "sports": "https://clio.taila01894.ts.net:3010/",
    "arena": "https://clio.taila01894.ts.net:3010/",
    "fanstack": "https://clio.taila01894.ts.net:3009/",
    "creator": "https://clio.taila01894.ts.net:3009/",
    "approvals": "https://clio.taila01894.ts.net:3027/",
    "mard": "https://clio.taila01894.ts.net:3028/",
    "listen": f"http://{CLIO_IP}:3040/",
    "collab": "https://collab.stacklabsllc.com/",
    "meet": "https://meet.stacklabsllc.com/"
}

def run_sentry(url: str, output_local: str, width: int = 1920, height: int = 1080, wait_ms: int = 3000, click: str = None):
    # Rewrite loopback/IP URLs to Tailscale MagicDNS or Clio's Tailscale IP
    target_url = url
    for prefix_pat in ["http://127.0.0.1:", "https://127.0.0.1:", "http://localhost:", "https://localhost:", "http://clio:", "https://clio:", "http://100.111.248.60:", "https://100.111.248.60:", "http://100.73.155.70:", "https://100.73.155.70:"]:
        if target_url.startswith(prefix_pat):
            port_rest = target_url[len(prefix_pat):]
            port_num = port_rest.split("/")[0].split("?")[0]
            if port_num in ["8088", "8090", "8095", "3004", "3017", "3026", "3027", "3029", "3033", "3035", "3300", "8443", "8446"]:
                target_url = f"https://clio.taila01894.ts.net:{port_rest}"
            else:
                prefix = "https://" if target_url.startswith("https") else "http://"
                target_url = f"{prefix}{CLIO_IP}:{port_rest}"
            break

    os.makedirs(os.path.dirname(os.path.abspath(output_local)), exist_ok=True)
    filename = os.path.basename(output_local)
    remote_out = f"/home/james/sovereign_sentry/captures/{filename}"
    
    remote_cmd_parts = [
        REMOTE_VENV,
        REMOTE_SCRIPT,
        "--url", target_url,
        "--out", remote_out,
        "--width", str(width),
        "--height", str(height),
        "--wait", str(wait_ms)
    ]
    if click:
        remote_cmd_parts.extend(["--click", click])
        
    remote_cmd_str = " ".join(shlex.quote(p) for p in remote_cmd_parts)
    
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
        f"{PEGASUS_USER}@{PEGASUS_IP}",
        remote_cmd_str
    ]

    
    print(f"[{datetime.now().isoformat()}] 🦅 Dispatching Pegasus Visual Sentry to: {url} ({width}x{height})...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode != 0:
        print(f"❌ SSH Execution Error:\n{res.stderr}")
        return None
        
    try:
        report = json.loads(res.stdout)
    except Exception:
        print(f"⚠️ Raw Output:\n{res.stdout}")
        return None

    # Pull screenshot from Pegasus to Clio
    scp_cmd = [
        "scp", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
        f"{PEGASUS_USER}@{PEGASUS_IP}:{remote_out}",
        output_local
    ]
    subprocess.run(scp_cmd, capture_output=True)
    
    if os.path.exists(output_local):
        report["local_screenshot"] = output_local
        print(f"✔ Screenshot captured by Pegasus and retrieved to Clio: {output_local} ({os.path.getsize(output_local):,} bytes)")
    
    return report

def run_dual_sentry(url: str, base_output_path: str, wait_ms: int = 3000, click: str = None):
    """
    Dispatches dual viewport sentry captures:
      - Desktop: 1920x1080 -> <base>_desktop.png
      - Mobile:  390x844   -> <base>_mobile.png
    Returns a dict containing both reports: {"desktop": desktop_report, "mobile": mobile_report}
    """
    if base_output_path.endswith(".png"):
        base_prefix = base_output_path[:-4]
    else:
        base_prefix = base_output_path

    desktop_out = f"{base_prefix}_desktop.png"
    mobile_out = f"{base_prefix}_mobile.png"

    print(f"\n=======================================================")
    print(f"🖥️  [DUAL SENTRY 1/2] Capturing Desktop Viewport (1920x1080)...")
    print(f"=======================================================")
    desktop_report = run_sentry(url, desktop_out, width=1920, height=1080, wait_ms=wait_ms, click=click)

    print(f"\n=======================================================")
    print(f"📱 [DUAL SENTRY 2/2] Capturing Mobile Viewport (390x844)...")
    print(f"=======================================================")
    mobile_report = run_sentry(url, mobile_out, width=390, height=844, wait_ms=wait_ms, click=click)

    return {
        "desktop": desktop_report,
        "mobile": mobile_report
    }

def print_report(report):
    if not report:
        print("❌ No report returned.")
        return
    print("\n=======================================================")
    print(f"🦅 PEGASUS VISUAL UAT REPORT — {report.get('page_title')}")
    print("=======================================================")
    print(f"• Node:            {report.get('node')}")
    print(f"• Target URL:      {report.get('url')}")
    print(f"• Viewport:        {report.get('viewport')}")
    print(f"• KI-095 Viewport: {'✔ PASSED (Zero browser scrollbars)' if report.get('ki095_compliant') else '❌ FAILED (Browser scrollbars detected)'}")
    print(f"• Console Errors:  {report.get('console_errors_count')}")
    if report.get('console_errors'):
        for err in report.get('console_errors'):
            print(f"    - {err}")
    print(f"• Duration:        {report.get('duration_sec')}s")
    print(f"• Local Path:      {report.get('local_screenshot')}")
    print("=======================================================\n")

def main():
    parser = argparse.ArgumentParser(description="Pegasus Visual Sentry Client")
    parser.add_argument("--room", choices=list(ROOM_URLS.keys()), help="Preset portal room")
    parser.add_argument("--url", help="Direct URL")
    parser.add_argument("--out", "--output", default=None, help="Local output PNG path")
    parser.add_argument("--ticket-id", "--ticket", dest="ticket_id", default=None, help="Associated SDLC Ticket ID")
    parser.add_argument("--port", type=int, default=None, help="Port on Clio (e.g. 3009)")
    parser.add_argument("--route", default=None, help="Route path e.g. /?room=creator_cockpit")
    parser.add_argument("--width", type=int, default=1920, help="Viewport width")
    parser.add_argument("--height", type=int, default=1080, help="Viewport height")
    parser.add_argument("--viewport", choices=["desktop", "mobile"], default=None, help="Viewport profile: desktop (1920x1080) or mobile (390x844)")
    parser.add_argument("--dual", action="store_true", help="Capture both Desktop (1920x1080) and Mobile (390x844)")
    parser.add_argument("--mobile", action="store_true", help="Capture Mobile viewport (390x844)")
    parser.add_argument("--click", "--selector", dest="click", default=None, help="Optional selector to click")
    parser.add_argument("--name", default=None, help="Descriptive name for output file")
    parser.add_argument("--wait", type=int, default=3000, help="Wait milliseconds before capture")
    
    args = parser.parse_args()
    
    if args.port:
        route = args.route or ""
        if route and not route.startswith("/"):
            route = "/" + route
        scheme = "https" if args.port in [3009, 3010, 3016, 3025, 3028] else "http"
        target_url = f"{scheme}://127.0.0.1:{args.port}{route}"
    else:
        target_url = args.url or (ROOM_URLS.get(args.room) if args.room else ROOM_URLS["kanban"])
    
    if args.out:
        out_path = args.out
    elif args.ticket_id:
        out_path = f"/home/james/stacklabs_inbox/tickets/{args.ticket_id}/mockups/pegasus_uat_{args.room or 'portal'}.png"
    elif args.name:
        if args.name == "horizon_evidence_drawer":
            out_path = "/home/james/stacklabs/mockups/pegasus_uat_wo0010476_drawer.png"
        else:
            out_path = f"/home/james/stacklabs/mockups/pegasus_uat_{args.name}.png"
    elif args.port or args.route:
        room_tag = args.room or (args.route.split("room=")[-1].split("&")[0] if args.route and "room=" in args.route else "creator_cockpit")
        out_path = f"/home/james/stacklabs/mockups/pegasus_uat_{room_tag}.png"
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = f"/home/james/stacklabs/screenshots/pegasus_uat_{args.room or 'portal'}_{ts}.png"
        
    if args.dual or args.name or (args.port and not args.mobile and args.viewport != "mobile"):
        reports = run_dual_sentry(target_url, out_path, wait_ms=args.wait, click=args.click)
        if reports.get("desktop"):
            print_report(reports["desktop"])
        if reports.get("mobile"):
            print_report(reports["mobile"])
    else:
        is_mobile = args.mobile or args.viewport == "mobile"
        width = 390 if is_mobile else args.width
        height = 844 if is_mobile else args.height
        report = run_sentry(target_url, out_path, width, height, wait_ms=args.wait, click=args.click)
        if report:
            print_report(report)

if __name__ == "__main__":
    main()
