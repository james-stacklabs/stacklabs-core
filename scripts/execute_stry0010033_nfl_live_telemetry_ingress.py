#!/usr/bin/env python3
"""
Sovereign OS — Autonomous Execution Hook
Work Order: STRY0010033-FANCAST-NFL-LIVE-TELEMETRY-INGRESS
Description: Validate Dual-Mode NFL live telemetry and video-synced replay ingress pipeline,
             verify Vite/React production build, capture Pegasus live visual twin,
             reconcile JIT approval, and resolve ticket in sovereign_now.db.
"""

import os
import sys
import subprocess
import time
import shutil
from datetime import datetime

sys.path.insert(0, '/home/james/stacklabs')
from scripts.core import api_client

TICKET_ID = "STRY0010033-FANCAST-NFL-LIVE-TELEMETRY-INGRESS"
APPR_ID = "appr_9412e049b6a1"
SPORTS_DIR = "/home/james/stacklabs/19_Sovereign_Sports"
BRAIN_DIR = "/home/james/.gemini/antigravity-ide/brain/62856916-9c87-4052-93af-a70b51da9215"

def verify_endpoints():
    print("🧪 1. Verifying dual-mode NFL telemetry via api_client...")
    res_replay = api_client.get_nfl_live_state("401873284", mode="replay", play=5)
    print(f"✔ Replay Play 5: status={res_replay.get('status')} | source={res_replay.get('source')} | play={res_replay.get('game', {}).get('last_play')}")
    assert res_replay.get("status") == "SUCCESS", "Replay mode failed"

    res_live = api_client.get_nfl_live_state("401873284", mode="live")
    print(f"✔ Live Ingress: status={res_live.get('status')} | source={res_live.get('source')} | game={res_live.get('game', {}).get('away_team')} @ {res_live.get('game', {}).get('home_team')}")
    assert res_live.get("status") == "SUCCESS", "Live mode failed"

def verify_build():
    print("🔨 2. Running production build in 19_Sovereign_Sports...")
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
    print("📸 3. Dispatching Pegasus Visual Sentry (100.96.77.20) for Rule IV.2.b Live Visual Twin...")
    sports_url = "https://clio.taila01894.ts.net:3010/?_game_room=401873284"
    filename = "pegasus_visual_twin_stry0010033_nfl_match_center.png"
    
    twin_res = api_client.capture_and_upload_ticket_twin(
        ticket_id=TICKET_ID,
        url=sports_url,
        filename=filename,
        wait_ms=5000
    )
    
    local_path = twin_res.get('local_path')
    print(f"✔ Pegasus Visual Twin Captured: {local_path}")
    print(f"✔ KI-095 Compliance Verified: {twin_res.get('ki095_compliant')}")
    
    # Copy to brain dir for artifact embedding
    if local_path and os.path.exists(local_path):
        brain_path = os.path.join(BRAIN_DIR, filename)
        shutil.copy(local_path, brain_path)
        print(f"✔ Visual Twin copied to brain artifact dir: {brain_path}")
        
    if not twin_res.get("ki095_compliant"):
        raise ValueError("KI-095 Viewport Violation: Outer browser scrollbars detected by Pegasus!")
        
    return twin_res

def reconcile_sdlc(twin_res=None):
    print("📋 4. Reconciling approval and ticket in sovereign_now.db...")
    try:
        api_client.update_approval(APPR_ID, state="Executed", auth_level="omega=1")
        print(f"✔ JIT Approval {APPR_ID} reconciled to Executed (omega=1)")
    except Exception as e:
        print(f"⚠️ Approval update notice: {e}")

    resolution_notes = (
        "RESOLVED: Deployed FanCast NFL Real-Time Telemetry & Video-Synced Replay Ingress Engine. "
        "Exposed GET /api/nfl/live/{game_pk} on Port 8095 supporting ?mode=live (5s TTL cache against live ESPN summary) "
        "and ?mode=replay (frame-by-frame 15-play drive playback from cached nfl_drive_replay.json ledger). "
        "Overhauled NflGridironMatchCenter.tsx with dynamic SVG line of scrimmage (blue), 1st down marker (gold), "
        "down/distance badge, possession indicators, and interactive Live vs Replay drive controls. "
        "Empirically validated with npm run build (0 errors) and attached verified Pegasus Playwright live visual twin "
        "(pegasus_visual_twin_stry0010033_nfl_match_center.png) asserting KI-095 locked viewport compliance."
    )
    try:
        api_client.resolve_ticket(TICKET_ID, resolution_notes)
        print(f"✔ Ticket {TICKET_ID} resolved successfully via FastAPI!")
    except Exception as e:
        print(f"⚠️ Ticket resolution notice: {e}")

def main():
    print(f"[{datetime.now().isoformat()}] 🚀 Executing {TICKET_ID}...")
    verify_endpoints()
    verify_build()
    twin_res = capture_pegasus_visual_twin()
    reconcile_sdlc(twin_res)
    print(f"🎉 {TICKET_ID} execution complete!")

if __name__ == "__main__":
    main()
