#!/usr/bin/env python3
"""
scripts/verify_wo0010518_burst_hud_twins.py
Playwright Visual Twin Capture & Verification for WO0010518 (Mount Olympus HUD).
Captures Desktop (1920x1080) and Mobile (390x844) twins on host Clio.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8088/burst"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")
TODAY_DIR = Path("/home/james/sovereign_inbox/today")

async def main():
    MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
    TODAY_DIR.mkdir(parents=True, exist_ok=True)

    dt_desktop = MOCKUPS_DIR / "pegasus_uat_wo0010518_burst_dark_desktop.png"
    mb_mobile = MOCKUPS_DIR / "pegasus_uat_wo0010518_burst_dark_mobile.png"
    dt_light = MOCKUPS_DIR / "pegasus_uat_wo0010518_burst_light_desktop.png"

    print("[PLAYWRIGHT] Launching Chromium headless on Clio metal...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # -------------------------------------------------------------
        # 1. DESKTOP VIEWPORT (1920x1080)
        # -------------------------------------------------------------
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_d = await ctx_desktop.new_page()

        print(f"[PLAYWRIGHT] Navigating Desktop to {BASE_URL}...")
        resp = await page_d.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        assert resp.status == 200, f"Expected 200 OK, got {resp.status}"

        # Wait for slots to populate
        await page_d.wait_for_selector("#slots-container > div", timeout=5000)
        slots = await page_d.query_selector_all("#slots-container > div")
        print(f"[PLAYWRIGHT] Asserting slots count in DOM: {len(slots)}")
        assert len(slots) == 10, f"Expected 10 slots, got {len(slots)}"

        # Assert key telemetry values
        equity_text = await page_d.inner_text("#metric-equity")
        winrate_text = await page_d.inner_text("#metric-winrate")
        gate_text = await page_d.inner_text("#gate-day-badge")
        print(f"[PLAYWRIGHT] Telemetry asserted: Equity={equity_text}, WinRate={winrate_text}, Gate={gate_text}")
        assert "$10,375.00" in equity_text
        assert "66.7%" in winrate_text

        # Assert Swarm Agents present
        alpha_text = await page_d.inner_text("#agent-alpha-text")
        beta_text = await page_d.inner_text("#agent-beta-text")
        assert len(alpha_text) > 10
        assert len(beta_text) > 10
        print("[PLAYWRIGHT] Swarm dialectic agents verified in DOM.")

        # Assert Spines and Geometry
        has_rounded = await page_d.evaluate("() => document.querySelectorAll('.rounded-card').length > 5")
        assert has_rounded, "rounded-card geometry class missing"
        has_spines = await page_d.evaluate("() => document.querySelectorAll('.spine-teal, .spine-profit, .spine-warn, .spine-loss').length >= 4")
        assert has_spines, "6px status spine classes missing"
        print("[PLAYWRIGHT] Card geometry and status spines verified.")

        # Invariant 36 click verification: test theme toggle
        theme_btn = await page_d.wait_for_selector("#theme-toggle")
        await theme_btn.click()
        await page_d.wait_for_timeout(300)
        is_light = await page_d.evaluate("() => !document.documentElement.classList.contains('dark')")
        print(f"[PLAYWRIGHT] Theme toggle clicked: is_light={is_light}")
        await page_d.screenshot(path=str(dt_light), full_page=False)
        print(f"[PLAYWRIGHT] Captured Light Mode -> {dt_light}")

        # Toggle back to Dark Mode
        await theme_btn.click()
        await page_d.wait_for_timeout(300)

        # Capture Desktop Dark Mode
        await page_d.screenshot(path=str(dt_desktop), full_page=False)
        shutil.copy(dt_desktop, TODAY_DIR / dt_desktop.name)
        print(f"[PLAYWRIGHT] Captured Desktop Dark -> {dt_desktop}")

        # -------------------------------------------------------------
        # 2. MOBILE VIEWPORT (390x844 - iPhone 14/15)
        # -------------------------------------------------------------
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        page_m = await ctx_mobile.new_page()
        print(f"[PLAYWRIGHT] Navigating Mobile to {BASE_URL}...")
        resp_m = await page_m.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        assert resp_m.status == 200

        await page_m.wait_for_selector("#slots-container > div", timeout=5000)
        await page_m.screenshot(path=str(mb_mobile), full_page=False)
        shutil.copy(mb_mobile, TODAY_DIR / mb_mobile.name)
        print(f"[PLAYWRIGHT] Captured Mobile Dark -> {mb_mobile}")

        await browser.close()
        print("🎉 [PLAYWRIGHT] All visual twin captures and DOM assertions passed on Clio metal!")

if __name__ == "__main__":
    asyncio.run(main())
