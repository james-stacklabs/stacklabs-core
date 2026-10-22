#!/usr/bin/env python3
"""
Verification Script & Playwright Visual Twin Sentry for WO0010529.
Work Order: WO0010529 — WIRE CFB & MLB SLATE TO FAAS CONSOLE (PORT 3033)
Assigned: Aggie (agy on Clio Metal Forge)

Asserts:
1. Schedule API returns >= 3 CFB games ('sport': 'cfb').
2. Schedule API returns >= 1 MLB game ('sport': 'mlb').
3. Schedule API does NOT contain 'nfl_2026_w04_pit_cle'.
4. CFB live telemetry endpoint /api/cfb/live/{game_id} responds with valid game telemetry.
5. Captures dual Playwright visual twins on metal:
   - Desktop (1920x1080): /home/james/stacklabs/mockups/pegasus_uat_wo0010529_faas_cfb_mlb_desktop.png
   - Mobile (390x844): /home/james/stacklabs/mockups/pegasus_uat_wo0010529_faas_cfb_mlb_mobile.png
"""

import os
import sys
import json
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:3033"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")
MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP_PNG = MOCKUPS_DIR / "pegasus_uat_wo0010529_faas_cfb_mlb_desktop.png"
MOBILE_PNG = MOCKUPS_DIR / "pegasus_uat_wo0010529_faas_cfb_mlb_mobile.png"

def verify_api_endpoints():
    print("[1/3] Verifying /api/mlb/schedule and CFB telemetry...")
    sched_url = f"{BASE_URL}/api/mlb/schedule"
    req = urllib.request.Request(sched_url, headers={"User-Agent": "FanStack/2.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"Expected 200 from {sched_url}, got {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))

    cfb_games = [g for g in data if g.get("sport") == "cfb"]
    mlb_games = [g for g in data if g.get("sport") == "mlb"]
    stale_nfl = [g for g in data if g.get("id") == "nfl_2026_w04_pit_cle"]

    print(f"  [+] Total Schedule Cards: {len(data)}")
    print(f"  [+] CFB Games: {len(cfb_games)}")
    print(f"  [+] MLB Games: {len(mlb_games)}")
    print(f"  [+] Stale NFL Matches: {len(stale_nfl)}")

    assert len(cfb_games) >= 3, f"Expected at least 3 CFB games, found {len(cfb_games)}"
    assert len(mlb_games) >= 1, f"Expected at least 1 MLB game, found {len(mlb_games)}"
    assert len(stale_nfl) == 0, f"Found stale NFL matchup nfl_2026_w04_pit_cle in schedule!"

    print("  ✓ CFB and MLB schedule assertion passed (zero stale NFL).")

    # Test CFB live endpoint
    first_cfb = cfb_games[0]
    cfb_id = first_cfb["id"]
    live_url = f"{BASE_URL}/api/cfb/live/{cfb_id}"
    req_live = urllib.request.Request(live_url, headers={"User-Agent": "FanStack/2.0"})
    with urllib.request.urlopen(req_live, timeout=10) as resp:
        assert resp.status == 200, f"Expected 200 from {live_url}, got {resp.status}"
        live_data = json.loads(resp.read().decode("utf-8"))
        print(f"  [+] CFB Live Data: {live_data.get('awayTeam')} vs {live_data.get('homeTeam')} | Score: {live_data.get('awayScore')}-{live_data.get('homeScore')} | Down: {live_data.get('downDistanceText')}")
        assert "down" in live_data
        assert "distance" in live_data
        assert "possession" in live_data
        assert "lastPlay" in live_data

    print("  ✓ CFB Live Telemetry endpoint assertion passed.")
    return cfb_games

def capture_visual_twins():
    print("[2/3] Launching Playwright Chromium Sentry for Visual Twins...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # 1. Desktop Viewport (1920x1080)
        print("  [*] Capturing Desktop Visual Twin (1920x1080)...")
        context_desk = browser.new_context(viewport={"width": 1920, "height": 1080})
        page_desk = context_desk.new_page()
        page_desk.goto(f"{BASE_URL}/?view=gameroom", wait_until="networkidle", timeout=15000)
        page_desk.wait_for_timeout(2000)

        # Assert slate ribbon presence
        assert page_desk.is_visible("text=ALL FEEDS"), "Slate ribbon not loaded on desktop!"
        # Screenshot
        page_desk.screenshot(path=str(DESKTOP_PNG), full_page=False)
        print(f"  ✓ Saved Desktop Visual Twin: {DESKTOP_PNG}")
        context_desk.close()

        # 2. Mobile Viewport (390x844 - iPhone 14 / modern mobile)
        print("  [*] Capturing Mobile Visual Twin (390x844)...")
        context_mob = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page_mob = context_mob.new_page()
        page_mob.goto(f"{BASE_URL}/?view=gameroom", wait_until="networkidle", timeout=15000)
        page_mob.wait_for_timeout(2000)

        # Assert slate ribbon presence
        assert page_mob.is_visible("text=ALL FEEDS"), "Slate ribbon not loaded on mobile!"
        # Screenshot
        page_mob.screenshot(path=str(MOBILE_PNG), full_page=False)
        print(f"  ✓ Saved Mobile Visual Twin: {MOBILE_PNG}")
        context_mob.close()

        browser.close()

def main():
    print("=" * 65)
    print("WO0010529: VERIFICATION ON METAL & PEGASUS DUAL-VIEWPORT GATE")
    print("=" * 65)

    cfb_games = verify_api_endpoints()
    capture_visual_twins()

    print("[3/3] Asserting Visual Twin Artifacts Exist on Disk...")
    assert DESKTOP_PNG.exists() and DESKTOP_PNG.stat().st_size > 10000, f"Desktop twin missing or too small: {DESKTOP_PNG}"
    assert MOBILE_PNG.exists() and MOBILE_PNG.stat().st_size > 10000, f"Mobile twin missing or too small: {MOBILE_PNG}"

    print(f"  ✓ Desktop Twin Size: {DESKTOP_PNG.stat().st_size} bytes")
    print(f"  ✓ Mobile Twin Size: {MOBILE_PNG.stat().st_size} bytes")
    print("=" * 65)
    print("ALL VERIFICATION GATES PASSED (100% GREEN)")
    print("=" * 65)

if __name__ == "__main__":
    main()
