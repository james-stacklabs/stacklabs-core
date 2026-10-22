#!/usr/bin/env python3
"""
Sovereign OS — Autonomous Execution Hook
Work Order: WO0010067-FANCAST-JETEXTRACTORS-STREAM-RESOLV
Description: FanCast Native JetExtractors Live Sports Stream Auto-Resolver Service.
             Deploys standalone Python resolver engine, exposes FastAPI endpoints on Port 8095,
             integrates Auto-Resolver deck in UniversalStreamDrawer.tsx on Port 3010,
             verifies build, captures Pegasus visual twin, and reconciles SDLC ticket.
"""

import os
import sys
import subprocess
import time
from datetime import datetime

sys.path.insert(0, '/home/james/stacklabs')
from scripts.core import api_client

TICKET_ID = "WO0010067-FANCAST-JETEXTRACTORS-STREAM-RESOLV"
APPR_ID = "appr_wo0010067_fancast_jetextractors_stream_resolv"
SPORTS_DIR = "/home/james/stacklabs/19_Sovereign_Sports"

def verify_resolver_api():
    print(f"[{datetime.now().isoformat()}] 🔍 1. Verifying JetExtractors FastAPI REST endpoint on Port 8095...")
    res = api_client.resolve_sports_stream("mlb", "mets")
    if res.get("status") != "success" or not res.get("sources"):
        raise ValueError(f"Resolver API verification failed: {res}")
    print(f"✔ Resolver API verified! Found {len(res['sources'])} candidate feeds for {res.get('game_title')}")
    return res

def verify_frontend_build():
    print(f"[{datetime.now().isoformat()}] 🔨 2. Running production build in 19_Sovereign_Sports...")
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
    print(f"[{datetime.now().isoformat()}] 📸 3. Dispatching Pegasus Visual Sentry (100.96.77.20) for Rule IV.2.b & Rule IV.12...")
    target_url = "https://clio.taila01894.ts.net:3010/mlb?fancam=true&resolver=true"
    filename = "pegasus_visual_twin_wo0010067_resolver.png"
    
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
    print(f"[{datetime.now().isoformat()}] 📋 4. Reconciling JIT approval and SDLC ticket in sovereign_now.db...")
    try:
        api_client.update_approval(APPR_ID, state="Executed", auth_level="omega=1")
        print(f"✔ JIT Approval {APPR_ID} reconciled to Executed (omega=1)")
    except Exception as e:
        print(f"⚠️ Approval update notice: {e}")

    resolution_notes = (
        "RESOLVED: Deployed FanCast Native JetExtractors Live Sports Stream Auto-Resolver Service. "
        "Engineered standalone Python resolver engine (/scripts/sports/resolvers/jetextractors_resolver.py) "
        "adapted from deobfuscated Mad Titan & The Loop plugins featuring Dean Edwards JS unpacker, regex HLS parser, "
        "and custom HTTP header bundler. Mounted REST endpoints GET /api/stream/resolve/{league}/{team} and "
        "GET /api/stream/sources on Port 8095 in sdlc_portal_server.py. Overhauled UniversalStreamDrawer.tsx on Port 3010 "
        "with dedicated [⚡ Auto-Resolver] deck, multi-league/team selectors, candidate stream feeds, manifest details box, "
        "and 1-click HLS playback with xhrSetup header injection. Verified with npm run build (0 errors) and captured "
        "verified Pegasus Playwright live visual twin asserting KI-095 compliance (0 scrollbars)."
    )
    try:
        api_client.resolve_ticket(TICKET_ID, resolution_notes)
        print(f"✔ Ticket {TICKET_ID} resolved successfully via FastAPI!")
    except Exception as e:
        print(f"⚠️ Ticket resolution notice: {e}")

def main():
    print(f"[{datetime.now().isoformat()}] 🚀 Executing {TICKET_ID}...")
    verify_resolver_api()
    verify_frontend_build()
    twin_res = capture_pegasus_visual_twin()
    reconcile_sdlc(twin_res)
    print(f"🎉 {TICKET_ID} execution complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
