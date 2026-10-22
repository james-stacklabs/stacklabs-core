#!/usr/bin/env python3
"""
Playwright automated verification script for Compact K.I.S.S. Gridiron HUD & Real Estate Restoration.
Work Order: WO0010479
Captures dual visual twins (Desktop & Mobile) and asserts UI integrity and compact hero height on metal.
"""

import os
import sys
from playwright.sync_api import sync_playwright

def run_verification():
    mockups_dir = "/home/james/stacklabs/mockups"
    os.makedirs(mockups_dir, exist_ok=True)
    desktop_png = os.path.join(mockups_dir, "pegasus_uat_compact_gridiron_desktop.png")
    mobile_png = os.path.join(mockups_dir, "pegasus_uat_compact_gridiron_mobile.png")

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

        # Select NFL Game
        pill_selector = "#nfl_2026_w04_pit_cle"
        page_desk.wait_for_selector(pill_selector, timeout=5000)
        print("  [+] Located #nfl_2026_w04_pit_cle slate pill")
        page_desk.click(pill_selector)
        page_desk.wait_for_timeout(1000)

        # Assert Gridiron HUD presence
        assert page_desk.is_visible("text=GRIDIRON HUD"), "GRIDIRON HUD header not visible!"
        print("  [+] Asserted 'GRIDIRON HUD'")

        # Assert Compact QB stats
        assert page_desk.is_visible("text=A. Rodgers"), "A. Rodgers QB card not visible!"
        assert page_desk.is_visible("text=D. Watson"), "D. Watson QB card not visible!"
        print("  [+] Asserted Away QB (A. Rodgers) & Home QB (D. Watson) cards")

        # Assert Compact Mini-Field SVG
        svg_el = page_desk.locator("svg[viewBox='0 0 160 76']")
        assert svg_el.count() > 0, "Compact 160x76 mini-field SVG not found!"
        print("  [+] Asserted Compact 160x76 Mini-Field SVG")

        # Assert Stacked Cards are stripped from Upper Hero
        assert not page_desk.is_visible("text=SAMMY THE SAVANT // UNDER 38.5 LOCK"), "Sammy banner should NOT be stacked in upper hero!"
        assert not page_desk.is_visible("text=KALSHI CFTC-DCM DIVERGENCE RADAR"), "Kalshi card should NOT be stacked in upper hero!"
        print("  [+] Verified Kalshi and Sammy cards stripped from upper hero (No 450px vertical stack!)")

        # Check LiveGridironHUD height is compact (~145px)
        hud_box = page_desk.locator("text=GRIDIRON HUD").locator("xpath=ancestor::div[contains(@class, 'h-[145px]')]").first.bounding_box()
        if hud_box:
            print(f"  [+] LiveGridironHUD measured height: {hud_box['height']}px (Target: ~145px)")
            assert 140 <= hud_box['height'] <= 165, f"HUD height {hud_box['height']}px is outside target range (~145px)!"

        # Assert Play-by-Play area has visibility
        assert page_desk.is_visible("text=PLAY-BY-PLAY"), "Play-by-play tab not visible!"
        print("  [+] Verified Play-by-Play is clearly visible")

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
        assert page_mob.is_visible("text=A. Rodgers"), "Mobile A. Rodgers not visible!"
        print("  [+] Asserted Mobile Gridiron HUD and QB telemetry")

        # Capture Mobile visual twin
        page_mob.screenshot(path=mobile_png)
        print(f"  [+] Mobile Visual Twin captured: {mobile_png}")
        context_mob.close()

        browser.close()

    print("\n✅ [PHYSICAL METAL VERIFICATION COMPLETE] Compact Gridiron HUD verified. Visual twins captured.")

if __name__ == "__main__":
    run_verification()
