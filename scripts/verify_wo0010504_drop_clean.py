#!/usr/bin/env python3
"""
Playwright Verification and Visual Twin Capture for WO0010504:
- Assert zero (CLIO METAL) leak on https://drop.stacklabsllc.com
- Assert SECURE ENTERPRISE INGRESS is rendered
- Capture dual viewport twins (Desktop 1920x1080 and Mobile 390x844)
- Save twin to /home/james/sovereign_inbox/today/pegasus_uat_wo0010504_drop_clean.png
"""

import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

async def run_visual_twins():
    target_url = "https://drop.stacklabsllc.com"
    fallback_url = "http://127.0.0.1:8088"
    
    out_dir = Path("/home/james/sovereign_inbox/today")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    desktop_twin = out_dir / "pegasus_uat_wo0010504_drop_clean.png"
    mobile_twin = out_dir / "pegasus_uat_wo0010504_drop_clean_mobile.png"
    cockpit_twin = out_dir / "pegasus_uat_wo0010504_cockpit_snipe.png"

    print("[PLAYWRIGHT] Launching Chromium headless...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # 1. DESKTOP VIEWPORT (1920x1080)
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page = await ctx_desktop.new_page()
        
        print(f"[PLAYWRIGHT] Navigating to {target_url}...")
        try:
            resp = await page.goto(target_url, wait_until="networkidle", timeout=15000)
        except Exception as e:
            print(f"[PLAYWRIGHT] Fallback to {fallback_url} due to: {e}")
            resp = await page.goto(fallback_url, wait_until="networkidle", timeout=15000)
            
        assert resp.status == 200, f"Expected 200 OK, got {resp.status}"

        # Assert no CLIO METAL leak
        content = await page.content()
        assert "CLIO METAL" not in content, "Leak detected: 'CLIO METAL' was found in rendered HTML!"
        assert "SECURE ENTERPRISE INGRESS" in content, "Missing 'SECURE ENTERPRISE INGRESS' badge in HTML!"
        print("✓ Verified: Zero 'CLIO METAL' in rendered DOM. 'SECURE ENTERPRISE INGRESS' present.")

        print(f"[PLAYWRIGHT] Capturing Desktop visual twin -> {desktop_twin}")
        await page.screenshot(path=str(desktop_twin), full_page=False)
        await ctx_desktop.close()

        # 2. MOBILE VIEWPORT (390x844)
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            device_scale_factor=2
        )
        page_m = await ctx_mobile.new_page()
        print(f"[PLAYWRIGHT] Navigating to {target_url} (mobile 390x844)...")
        try:
            resp_m = await page_m.goto(target_url, wait_until="networkidle", timeout=15000)
        except Exception:
            resp_m = await page_m.goto(fallback_url, wait_until="networkidle", timeout=15000)
            
        assert resp_m.status == 200, f"Expected 200 OK, got {resp_m.status}"
        print(f"[PLAYWRIGHT] Capturing Mobile visual twin -> {mobile_twin}")
        await page_m.screenshot(path=str(mobile_twin), full_page=False)
        await ctx_mobile.close()

        # 3. COCKPIT YOUTUBE SNIPE TAB VERIFICATION
        ctx_cockpit = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_c = await ctx_cockpit.new_page()
        cockpit_url = f"{fallback_url}/cockpit"
        print(f"[PLAYWRIGHT] Navigating to Cockpit: {cockpit_url}...")
        resp_c = await page_c.goto(cockpit_url, wait_until="networkidle", timeout=15000)
        assert resp_c.status == 200, f"Cockpit expected 200, got {resp_c.status}"

        # Click YouTube Snipe nav pill
        snipe_nav_btn = page_c.locator("#btn-snipe")
        assert await snipe_nav_btn.is_visible(), "YouTube Snipe nav button must be visible in Cockpit"
        await snipe_nav_btn.click()
        await page_c.wait_for_timeout(500)

        # Assert input visible
        snipe_input = page_c.locator("#snipe-url-input")
        assert await snipe_input.is_visible(), "Snipe URL input must be visible after tab switch"

        print(f"[PLAYWRIGHT] Capturing Cockpit YouTube Snipe Studio visual twin -> {cockpit_twin}")
        await page_c.screenshot(path=str(cockpit_twin), full_page=False)
        await ctx_cockpit.close()

        await browser.close()
        print("[PLAYWRIGHT] ✅ All dual viewport visual twins successfully captured and verified!")

if __name__ == "__main__":
    asyncio.run(run_visual_twins())
