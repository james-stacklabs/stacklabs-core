#!/usr/bin/env python3
"""
Sovereign OS — Autonomous Execution Hook
Work Order: WO0010064-FANCAST-FAN-REACTION-CAM-AND-STREAM
Description: Build & deploy Universal Multi-Source Stream Ingress (YouTube/Wardy, Twitch, HLS)
             and Pilot Fan Reaction Cam (C120 webcam) in 19_Sovereign_Sports & 15_FanStack,
             verify Vite build, capture Pegasus visual twin, and reconcile SDLC ticket.
"""

import os
import sys
import subprocess
import time
from datetime import datetime

sys.path.insert(0, '/home/james/stacklabs')
from scripts.core import api_client

TICKET_ID = "WO0010064-FANCAST-FAN-REACTION-CAM-AND-STREAM"
APPR_ID = "appr_wo0010064_fancast_reaction_cam"
SPORTS_DIR = "/home/james/stacklabs/19_Sovereign_Sports"

def verify_build():
    print(f"[{datetime.now().isoformat()}] 🔨 1. Running production build in 19_Sovereign_Sports...")
    build_cmd = subprocess.run(
        ["npm", "run", "build"],
        cwd=SPORTS_DIR,
        capture_output=True,
        text=True
    )
    if build_cmd.returncode != 0:
        print(f"❌ Build failed:\n{build_cmd.stderr}")
        sys.exit(1)
    print("✔ 19_Sovereign_Sports build succeeded with exit code 0!")

def capture_pegasus_visual_twin():
    print(f"[{datetime.now().isoformat()}] 📸 2. Dispatching Pegasus Visual Sentry (100.96.77.20) for Rule IV.2.b...")
    target_url = "https://clio.taila01894.ts.net:3010/mlb?fancam=true"
    filename = "pegasus_visual_twin_wo0010064_fancast_reaction_cam.png"
    
    twin_res = api_client.capture_and_upload_ticket_twin(
        ticket_id=TICKET_ID,
        url=target_url,
        filename=filename,
        wait_ms=5000
    )
    
    print(f"✔ Pegasus Visual Twin Captured: {twin_res.get('local_path')}")
    print(f"✔ KI-095 Compliance Verified: {twin_res.get('ki095_compliant')}")
    
    if not twin_res.get("ki095_compliant"):
        raise ValueError("KI-095 Viewport Violation: Outer browser scrollbars detected by Pegasus!")
        
    return twin_res

def reconcile_sdlc(twin_res=None):
    print(f"[{datetime.now().isoformat()}] 📋 3. Reconciling approval and ticket in sovereign_now.db...")
    try:
        api_client.update_approval(APPR_ID, state="Executed", auth_level="omega=1")
        print(f"✔ JIT Approval {APPR_ID} reconciled to Executed (omega=1)")
    except Exception as e:
        print(f"⚠️ Approval update notice: {e}")

    resolution_notes = (
        "RESOLVED: Deployed FanCast Universal Stream Ingress & Pilot Fan Reaction Cam Deck. "
        "Built UniversalStreamDrawer.tsx supporting multi-source feeds (YouTube Live/Wardy iframe embed, Twitch, HLS, direct MP4). "
        "Built PilotReactionCam.tsx integrating the Logitech C120 USB webcam (navigator.mediaDevices.getUserMedia / local bridge) "
        "with frosted glass framing and glowing cyan recording pulse. Mounted globally in SportsLayout.tsx with floating corner PiP, "
        "split ManningCast, and full theater view modes. Verified with npm run build (0 errors) and attached verified Pegasus "
        "Playwright live visual twin asserting KI-095 compliance."
    )
    try:
        api_client.resolve_ticket(TICKET_ID, resolution_notes)
        print(f"✔ Ticket {TICKET_ID} resolved successfully via FastAPI!")
    except Exception as e:
        print(f"⚠️ Ticket resolution notice: {e}")

def main():
    print(f"[{datetime.now().isoformat()}] 🚀 Executing {TICKET_ID}...")
    verify_build()
    twin_res = capture_pegasus_visual_twin()
    reconcile_sdlc(twin_res)
    print(f"🎉 {TICKET_ID} execution complete!")

if __name__ == "__main__":
    main()
