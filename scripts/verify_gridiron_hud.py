#!/usr/bin/env python3
"""
Playwright automated verification script for FanStack Multi-Sport Vector Engine (Gridiron HUD & Kalshi Divergence).
Work Order: WO0010478
Captures dual visual twins (Desktop & Mobile) and asserts UI integrity on metal.
"""

import sys
import os
from playwright.sync_api import sync_playwright

def run_verification():
    mockups_dir = "/home/james/stacklabs/mockups"
    os.makedirs(mockups_dir, exist_ok=True)
    desktop_png = os.path.join(mockups_dir, "pegasus_uat_gridiron_desktop.png")
    mobile_png = os.path.join(mockups_dir, "pegasus_uat_gridiron_mobile.png")

    target_url = "http://127.0.0.1:3032/?view=gameroom"

    print(f"[*] Launching Chromium sentry to test {target_url}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------------
        # 1. DESKTOP RUN (1920x1080)
        # -------------------------------------------------------------------
        print("[*] Running Desktop 1920x1080 Verification...")
        context_desk = browser.new_context(viewport={"width": 1920, "height": 1080})
        page_desk = context_desk.new_page()

        resp = page_desk.goto(target_url, wait_until="networkidle", timeout=15000)
        assert resp is not None and resp.status == 200, f"HTTP status failed: {resp.status if resp else 'No response'}"
        print(f"  [+] HTTP Status: {resp.status} OK")

        # Wait for SlateSwitcherRibbon and game pill
        pill_selector = "#nfl_2026_w04_pit_cle"
        page_desk.wait_for_selector(pill_selector, timeout=5000)
        print("  [+] Located #nfl_2026_w04_pit_cle slate pill")

        # Click the NFL game pill
        page_desk.click(pill_selector)
        page_desk.wait_for_timeout(1000)

        # Assert Gridiron HUD presence
        assert page_desk.is_visible("text=GRIDIRON HUD"), "GRIDIRON HUD header not visible!"
        assert page_desk.is_visible("text=100-YARD VECTOR ENGINE"), "100-YARD VECTOR ENGINE badge not visible!"
        print("  [+] Asserted 'GRIDIRON HUD' and '100-YARD VECTOR ENGINE'")

        # Assert SVG field presence
        svg_el = page_desk.locator("svg:has-text('STEELERS')")
        assert svg_el.count() > 0, "Gridiron SVG field with STEELERS text not found!"
        print("  [+] Asserted Gridiron SVG field elements")

        # Assert Line of Scrimmage and 1st down markers
        assert page_desk.is_visible("text=LINE OF SCRIMMAGE"), "LINE OF SCRIMMAGE legend not visible!"
        print("  [+] Asserted Gridiron HUD legend & scrimmage line")

        # Assert Kalshi Divergence Card
        assert page_desk.is_visible("text=KALSHI CFTC-DCM"), "KALSHI CFTC-DCM card not visible!"
        assert page_desk.is_visible("text=KXNFL-26W04-PITCLE-U38.5"), "Kalshi ticker not visible!"
        assert page_desk.is_visible("text=DIVERGENCE SPREAD"), "Divergence Spread metric not visible!"
        print("  [+] Asserted Kalshi Divergence Card & Ticker KXNFL-26W04-PITCLE-U38.5")

        # Assert Sammy The Savant Under 38.5 Lock Banner
        assert page_desk.is_visible("text=SAMMY THE SAVANT"), "Sammy The Savant banner not visible!"
        assert page_desk.is_visible("text=T.J. WATT"), "T.J. Watt defensive telemetry badge not visible!"
        print("  [+] Asserted Sammy The Savant Under 38.5 Lock Banner")

        # Capture Desktop visual twin
        page_desk.screenshot(path=desktop_png)
        print(f"  [+] Desktop Visual Twin captured: {desktop_png}")
        context_desk.close()

        # -------------------------------------------------------------------
        # 2. MOBILE RUN (390x844)
        # -------------------------------------------------------------------
        print("\n[*] Running Mobile 390x844 Verification...")
        context_mob = browser.new_context(viewport={"width": 390, "height": 844})
        page_mob = context_mob.new_page()

        resp_mob = page_mob.goto(target_url, wait_until="networkidle", timeout=15000)
        assert resp_mob is not None and resp_mob.status == 200, f"Mobile HTTP status failed: {resp_mob.status if resp_mob else 'No response'}"
        print(f"  [+] Mobile HTTP Status: {resp_mob.status} OK")

        page_mob.wait_for_selector(pill_selector, timeout=5000)
        page_mob.click(pill_selector)
        page_mob.wait_for_timeout(1000)

        assert page_mob.is_visible("text=GRIDIRON HUD"), "Mobile GRIDIRON HUD header not visible!"
        assert page_mob.is_visible("text=KALSHI CFTC-DCM"), "Mobile KALSHI CFTC-DCM not visible!"
        print("  [+] Asserted Mobile Gridiron HUD and Kalshi Divergence Card")

        # Capture Mobile visual twin
        page_mob.screenshot(path=mobile_png)
        print(f"  [+] Mobile Visual Twin captured: {mobile_png}")
        context_mob.close()

        browser.close()

    print("\n✅ [PHYSICAL METAL VERIFICATION COMPLETE] All assertions passed. Visual twins recorded.")

if __name__ == "__main__":
    run_verification()
