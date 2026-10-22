#!/usr/bin/env python3
"""
VERIFICATION SUITE: WO0011065
Replace Ugly Native Scrollbar with Chevron Scroll Arrows in Theater Deck Channel Ribbon
Host: Clio (Metal Forge)
"""

import sys
import subprocess
from pathlib import Path

FAAS_DIR = Path("/home/james/stacklabs/apps/faas")
THEATER_DECK_FILE = FAAS_DIR / "src" / "components" / "TheaterDeck.tsx"
PEGASUS_DECK_FILE = FAAS_DIR / "src" / "components" / "PegasusTheaterDeck.tsx"

def log(msg, success=True):
    color = "\033[92m✔" if success else "\033[91m✖"
    print(f"{color} {msg}\033[0m")

def test_theater_deck():
    print("\n--- TEST 1: THEATER DECK CODE INTEGRITY ---")
    assert THEATER_DECK_FILE.exists(), f"Missing {THEATER_DECK_FILE}"
    content = THEATER_DECK_FILE.read_text(encoding="utf-8")
    
    assert "ChevronLeft" in content, "Missing ChevronLeft import in TheaterDeck.tsx"
    assert "ChevronRight" in content, "Missing ChevronRight import in TheaterDeck.tsx"
    assert "channelScrollRef" in content, "Missing channelScrollRef in TheaterDeck.tsx"
    assert "scrollChannels" in content, "Missing scrollChannels in TheaterDeck.tsx"
    assert "handleChannelWheel" in content, "Missing handleChannelWheel in TheaterDeck.tsx"
    assert "scrollbar-none" in content, "Missing scrollbar-none class in TheaterDeck.tsx"
    assert "[&::-webkit-scrollbar]:hidden" in content, "Missing [&::-webkit-scrollbar]:hidden in TheaterDeck.tsx"
    assert "scrollbar-thin" not in content, "Found banned scrollbar-thin in TheaterDeck.tsx"
    
    log("TheaterDeck.tsx verified: chevron controls, smooth scroll, wheel handler, zero scrollbar-thin")
    return True

def test_pegasus_theater_deck():
    print("\n--- TEST 2: PEGASUS THEATER DECK MIRROR INTEGRITY ---")
    assert PEGASUS_DECK_FILE.exists(), f"Missing {PEGASUS_DECK_FILE}"
    content = PEGASUS_DECK_FILE.read_text(encoding="utf-8")
    
    assert "ChevronLeft" in content, "Missing ChevronLeft import in PegasusTheaterDeck.tsx"
    assert "ChevronRight" in content, "Missing ChevronRight import in PegasusTheaterDeck.tsx"
    assert "channelScrollRef" in content, "Missing channelScrollRef in PegasusTheaterDeck.tsx"
    assert "scrollChannels" in content, "Missing scrollChannels in PegasusTheaterDeck.tsx"
    assert "handleChannelWheel" in content, "Missing handleChannelWheel in PegasusTheaterDeck.tsx"
    assert "scrollbar-none" in content, "Missing scrollbar-none class in PegasusTheaterDeck.tsx"
    assert "[&::-webkit-scrollbar]:hidden" in content, "Missing [&::-webkit-scrollbar]:hidden in PegasusTheaterDeck.tsx"
    assert "scrollbar-thin" not in content, "Found banned scrollbar-thin in PegasusTheaterDeck.tsx"
    
    log("PegasusTheaterDeck.tsx verified: chevron controls, smooth scroll, wheel handler, zero scrollbar-thin")
    return True

def test_frontend_build():
    print("\n--- TEST 3: PRODUCTION BUILD VALIDATION ---")
    cmd = ["npm", "run", "build"]
    res = subprocess.run(cmd, cwd=str(FAAS_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        log(f"npm run build failed:\n{res.stderr}\n{res.stdout}", success=False)
        return False
    log("npm run build passed cleanly with code 0 (TypeScript + JSX + Vite)")
    return True

def main():
    print("=" * 70)
    print("⚡ THEATER DECK CHANNEL RIBBON CHEVRON ARROWS VERIFICATION (WO0011065)")
    print("=" * 70)

    tests = [
        ("Theater Deck Verification", test_theater_deck),
        ("Pegasus Theater Deck Verification", test_pegasus_theater_deck),
        ("Production Build Gate", test_frontend_build)
    ]

    all_passed = True
    for name, t_fn in tests:
        if not t_fn():
            all_passed = False
            break

    print("\n" + "=" * 70)
    if all_passed:
        print("\033[92m✔ ALL GATES PASSED: WO0011065 READY FOR PILOT SIGN-OFF\033[0m")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\033[91m✖ VERIFICATION FAILED: ONE OR MORE GATES REJECTED\033[0m")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    main()
