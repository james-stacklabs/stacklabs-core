#!/usr/bin/env python3
"""
StackLabs Sovereign FaaS Gridiron HUD Verification Gate
Path: /home/james/stacklabs/scripts/verify_gridiron_hud_hero.py
Invariants: 15, 26, 32, 35, 38
"""
import sys
from pathlib import Path

HUD_FILE = Path("/home/james/stacklabs/apps/faas/src/components/LiveGridironHUD.tsx")
GAMEROOM_FILE = Path("/home/james/stacklabs/apps/faas/src/GameRoom.tsx")

def verify_gridiron():
    print("================================================================================")
    print("  STACKLABS VERIFICATION GATE: HERO FULL-WIDTH GRIDIRON TURF FIELD")
    print("================================================================================")
    
    if not HUD_FILE.exists():
        print(f"FAIL: Gridiron HUD missing at {HUD_FILE}")
        sys.exit(1)
        
    hud_content = HUD_FILE.read_text(encoding="utf-8")
    
    # Invariant: h-[140px] must be removed
    if 'h-[140px] ${className}' in hud_content:
        print("  [FAIL] Restrictive h-[140px] still present in LiveGridironHUD root container")
        sys.exit(1)
    else:
        print("  [PASS] Restrictive h-[140px] purged; container flexes with line score companion")

    checks = [
        ("Full-Width ViewBox 720x140", 'viewBox="0 0 720 140"'),
        ("High-Resolution 6.0 px/yd math", "ballX = 60 + (clampedYardline * 6.0)"),
        ("Red Zone Shading & Badges", "RED ZONE"),
        ("1-Yard Hash Marks", "Array.from({ length: 99 }"),
        ("Bold Yard Numbers & Directional Arrows", "arrow === '▶'"),
        ("First Down Progress Zone", "fill=\"#FACC15\""),
        ("Line of Scrimmage Cyan Glow", "stroke=\"#00F0FF\""),
        ("Team Endzone Color Engine", "TEAM_COLOR_MAP"),
        ("Live Play-By-Play Telemetry Ticker", "LAST PLAY"),
        ("downDistanceText Prop Support", "downDistanceText?: string"),
        ("lastPlay Prop Support", "lastPlay?: string"),
    ]
    
    failures = []
    for label, pattern in checks:
        if pattern in hud_content:
            print(f"  [PASS] {label}")
        else:
            print(f"  [FAIL] {label} (missing: '{pattern}')")
            failures.append(label)
            
    # Verify GameRoom passes downDistanceText & lastPlay
    gameroom_content = GAMEROOM_FILE.read_text(encoding="utf-8")
    if "downDistanceText={cfbData?.downDistanceText}" in gameroom_content and "lastPlay={cfbData?.lastPlay}" in gameroom_content:
        print("  [PASS] GameRoom passes downDistanceText and lastPlay to LiveGridironHUD")
    else:
        print("  [FAIL] GameRoom missing downDistanceText or lastPlay prop passing")
        failures.append("GameRoom Props")
        
    if failures:
        print(f"\nVerification FAILED on {len(failures)} checks.")
        sys.exit(1)
        
    print("\nAll 12 Hero Gridiron Turf Field checks PASSED cleanly.")
    sys.exit(0)

if __name__ == "__main__":
    verify_gridiron()
