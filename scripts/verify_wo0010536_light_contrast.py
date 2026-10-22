#!/usr/bin/env python3
"""
scripts/verify_wo0010536_light_contrast.py
Playwright Visual Twin Capture & Verification for WO0010536
Purge Purple & Fix Light-Mode Contrast on Enterprise Drop Portal (Port 8088).
Captures Light Mode Desktop (1920x1080), Light Mode Mobile (390x844),
and Dark Mode Desktop (1920x1080) visual twins.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8088"
AUTH_QUERY = "?key=rudnicki2026&from=Pawel"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")
TODAY_DIR = Path("/home/james/sovereign_inbox/today")

async def capture_twins():
    MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
    TODAY_DIR.mkdir(parents=True, exist_ok=True)

    light_dt = MOCKUPS_DIR / "pegasus_uat_wo0010536_light_desktop.png"
    light_mb = MOCKUPS_DIR / "pegasus_uat_wo0010536_light_mobile.png"
    dark_dt = MOCKUPS_DIR / "pegasus_uat_wo0010536_dark_desktop.png"

    print("[PLAYWRIGHT] Launching Chromium headless on Clio metal...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        portal_url = f"{BASE_URL}/{AUTH_QUERY}"

        # -------------------------------------------------------------
        # 1. DESKTOP VIEWPORT (1920x1080) - LIGHT MODE & DARK MODE
        # -------------------------------------------------------------
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_d = await ctx_desktop.new_page()

        print(f"[PLAYWRIGHT] Navigating Desktop to Drop Portal: {portal_url}")
        resp = await page_d.goto(portal_url, wait_until="networkidle", timeout=15000)
        assert resp.status == 200, f"Expected 200, got {resp.status}"

        # Click Listen Tab
        print("[PLAYWRIGHT] Clicking #tabBtnListen...")
        await page_d.click("#tabBtnListen")
        await page_d.wait_for_timeout(600)

        # Switch to Light Mode
        print("[PLAYWRIGHT] Switching to Light Mode...")
        await page_d.evaluate("setTheme('light')")
        await page_d.wait_for_timeout(400)

        # Assert Listen pane is visible
        is_listen_visible = await page_d.evaluate("!document.getElementById('listenPane').classList.contains('hidden')")
        assert is_listen_visible, "listenPane must be visible!"

        # Assert bullets exist and are visible
        bullets = await page_d.query_selector_all("#briefBullets li")
        assert len(bullets) >= 3, f"Expected at least 3 bullets, got {len(bullets)}"

        # Assert no purple classes in the DOM
        purple_elements = await page_d.evaluate("""() => {
            const els = Array.from(document.querySelectorAll('*'));
            return els.filter(el => {
                const c = el.className;
                return typeof c === 'string' && c.toLowerCase().includes('purple');
            }).length;
        }""")
        assert purple_elements == 0, f"Detected {purple_elements} elements with purple classes!"
        print(f"[PLAYWRIGHT] Verified 0 purple elements on page in Light Mode.")

        # Check brief bullets text color contrast in Light Mode
        bullet_strong_color = await page_d.evaluate("""() => {
            const st = document.querySelector('#briefBullets strong');
            return st ? window.getComputedStyle(st).color : null;
        }""")
        print(f"[PLAYWRIGHT] Computed color of #briefBullets strong in Light Mode: {bullet_strong_color}")
        # RGB of text-slate-900 is rgb(15, 23, 42) -> NOT white rgb(255, 255, 255)
        assert bullet_strong_color != "rgb(255, 255, 255)", "Bullet strong text must NOT be white in Light Mode!"

        # Capture Desktop Light Twin (top)
        print(f"[PLAYWRIGHT] Capturing Desktop Light Mode Twin -> {light_dt}")
        await page_d.screenshot(path=str(light_dt), full_page=False)
        shutil.copy(light_dt, TODAY_DIR / light_dt.name)

        # Test CarPlay Modal in Light Mode
        print("[PLAYWRIGHT] Testing CarPlay Modal in Light Mode...")
        await page_d.click("button:has-text('Add to Apple Podcasts')")
        await page_d.wait_for_timeout(300)
        modal_visible = await page_d.evaluate("!document.getElementById('podcastModal').classList.contains('hidden')")
        assert modal_visible, "podcastModal must be visible!"
        light_modal_dt = MOCKUPS_DIR / "pegasus_uat_wo0010536_light_modal_desktop.png"
        await page_d.screenshot(path=str(light_modal_dt), full_page=False)
        shutil.copy(light_modal_dt, TODAY_DIR / light_modal_dt.name)
        await page_d.click("#podcastModal button:has-text('Close')")
        await page_d.wait_for_timeout(300)

        # Switch to Dark Mode
        print("[PLAYWRIGHT] Switching to Dark Mode...")
        await page_d.evaluate("setTheme('dark')")
        await page_d.wait_for_timeout(400)

        # Capture Desktop Dark Twin
        print(f"[PLAYWRIGHT] Capturing Desktop Dark Mode Twin -> {dark_dt}")
        await page_d.screenshot(path=str(dark_dt), full_page=False)
        shutil.copy(dark_dt, TODAY_DIR / dark_dt.name)

        await page_d.close()

        # -------------------------------------------------------------
        # 2. MOBILE VIEWPORT (390x844) - LIGHT MODE
        # -------------------------------------------------------------
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        page_m = await ctx_mobile.new_page()

        print(f"[PLAYWRIGHT] Navigating Mobile to Drop Portal: {portal_url}")
        resp_m = await page_m.goto(portal_url, wait_until="networkidle", timeout=15000)
        assert resp_m.status == 200, f"Expected 200, got {resp_m.status}"

        # Switch to Light Mode
        await page_m.evaluate("setTheme('light')")
        await page_m.wait_for_timeout(300)

        print("[PLAYWRIGHT] Clicking #tabBtnListen on Mobile...")
        await page_m.click("#tabBtnListen")
        await page_m.wait_for_timeout(600)

        is_m_listen_visible = await page_m.evaluate("!document.getElementById('listenPane').classList.contains('hidden')")
        assert is_m_listen_visible, "listenPane must be visible on mobile!"

        # Capture Mobile Light Twin
        print(f"[PLAYWRIGHT] Capturing Mobile Light Mode Twin -> {light_mb}")
        await page_m.screenshot(path=str(light_mb), full_page=False)
        shutil.copy(light_mb, TODAY_DIR / light_mb.name)

        await page_m.close()
        await browser.close()
        print("✅ [PLAYWRIGHT TWIN GATE] Desktop (Light & Dark) and Mobile (Light) twins verified successfully!")

if __name__ == "__main__":
    asyncio.run(capture_twins())
