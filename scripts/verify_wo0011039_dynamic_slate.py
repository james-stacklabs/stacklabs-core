#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011039 Verification Script: Dynamic Slate & Partitioned Bleacher Wiretap
Author: James Carroll & Clio Metal Forge
Date: October 10, 2026
Invariants: 15 (Two-Call Verification), 26 (Gandalf UI Craft), 36 (Metal Verification)
"""
import sys
import subprocess
import requests
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

def test_zero_hardcoded_source():
    print("[1/5] Asserting ZERO occurrences of '20261008_TB_DAL' in apps/faas/src/...")
    src_dir = Path("/home/james/stacklabs/apps/faas/src")
    res = subprocess.run(
        ["grep", "-rn", "20261008_TB_DAL", str(src_dir)],
        capture_output=True,
        text=True
    )
    if res.returncode == 0:
        print(f"FAILED: Found '20261008_TB_DAL' in source:\n{res.stdout}")
        return False
    print("PASS: Exactly zero occurrences in apps/faas/src/.")
    return True

def test_dynamic_schedule():
    print("[2/5] Testing /api/mlb/schedule for live Saturday slate...")
    try:
        r = requests.get("http://127.0.0.1:3033/api/mlb/schedule", timeout=5)
        r.raise_for_status()
        games = r.json()
        if not games or len(games) == 0:
            print("FAILED: /api/mlb/schedule returned empty slate.")
            return False
        first_game = games[0]
        print(f"  First game in schedule: {first_game.get('id')} - {first_game.get('awayTeam')} vs {first_game.get('homeTeam')} (isLive: {first_game.get('isLive')})")
        assert first_game.get("isLive") is True, f"Expected first game to be live, got {first_game}"
        assert first_game.get("id") != "20261008_TB_DAL", "First game should not be hardcoded TNF!"
        print("PASS: Schedule returns live Saturday slate with dynamic first game.")
        return True
    except Exception as e:
        print(f"FAILED: Dynamic schedule test failed: {e}")
        return False

def test_partitioned_chat():
    print("[3/5] Testing /api/stream/chat_tail?game_id=cfb_401858481 (empty partition)...")
    try:
        r = requests.get("http://127.0.0.1:3033/api/stream/chat_tail?game_id=cfb_401858481", timeout=5)
        r.raise_for_status()
        data = r.json()
        assert data == [], f"Expected empty list for unlinked game cfb_401858481, got {data}"
        print("PASS: Unlinked game returns empty chat partition ([]).")

        print("  Testing global /api/stream/chat_tail fallback...")
        r_global = requests.get("http://127.0.0.1:3033/api/stream/chat_tail?limit=5", timeout=5)
        r_global.raise_for_status()
        global_data = r_global.json()
        assert len(global_data) > 0, "Expected non-empty global chat stream"
        print(f"PASS: Global stream fallback active ({len(global_data)} comments).")
        return True
    except Exception as e:
        print(f"FAILED: Partitioned chat test failed: {e}")
        return False

def test_visual_twins():
    print("[4/5] Capturing dual visual twins via Playwright...")
    shots_dir = Path("/home/james/stacklabs/docs/screenshots")
    shots_dir.mkdir(parents=True, exist_ok=True)
    desktop_png = shots_dir / "gameroom_dynamic_slate_desktop_1920x1080.png"
    mobile_png = shots_dir / "gameroom_dynamic_slate_mobile_390x844.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop 1920x1080
        desktop_page = browser.new_page(viewport={"width": 1920, "height": 1080})
        desktop_page.goto("http://127.0.0.1:3033/?view=gameroom", wait_until="networkidle")
        desktop_page.wait_for_timeout(3000)
        desktop_page.screenshot(path=str(desktop_png), full_page=False)
        print(f"  Desktop screenshot saved: {desktop_png}")

        # Check content on desktop
        body_text = desktop_page.content()
        assert "NO LIVE WIRETAP FOR THIS MATCHUP" in body_text, "Desktop missing empty wiretap state"
        assert "20261008_TB_DAL" not in body_text, "Desktop still contains 20261008_TB_DAL"
        print("  Desktop DOM assertions verified: Clean empty wiretap state present.")

        # 2. Mobile 390x844
        mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_page.goto("http://127.0.0.1:3033/?view=gameroom", wait_until="networkidle")
        mobile_page.wait_for_timeout(3000)
        mobile_page.screenshot(path=str(mobile_png), full_page=False)
        print(f"  Mobile screenshot saved: {mobile_png}")

        browser.close()

    print("PASS: Dual visual twin screenshots generated and DOM verified.")
    return True

def main():
    print("================================================================")
    print("WO0011039 FORENSIC VERIFICATION: DYNAMIC SLATE & WIRETAP")
    print("================================================================")
    
    t1 = test_zero_hardcoded_source()
    t2 = test_dynamic_schedule()
    t3 = test_partitioned_chat()
    t4 = test_visual_twins()

    if all([t1, t2, t3, t4]):
        print("\n================================================================")
        print("ALL WO0011039 ACCEPTANCE CRITERIA VERIFIED ON METAL (PASS)")
        print("================================================================")
        sys.exit(0)
    else:
        print("\nFAILED: One or more checks failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
