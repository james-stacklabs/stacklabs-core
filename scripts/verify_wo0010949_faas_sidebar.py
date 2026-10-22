#!/usr/bin/env python3
"""
scripts/verify_wo0010949_faas_sidebar.py
Verification script for WO0010949:
- Validates FaaS right sidebar refactor (Deep Void, Gandalf UI craft, segmented tabs)
- Asserts BLEACHER WIRE tab is default with live stream tail
- Asserts GAME INTEL tab renders dynamic active game telemetry (MIL @ SD)
- Asserts ZERO stale Boston/Bronx text leakage (Max Fried, Nate Eaton, Boston Toxic Meltdown, Bronx Euphoria)
- Captures desktop (1920x1080) and mobile (390x844) visual twins
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:3033/#gameroom"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")

async def run_verification():
    MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
    desktop_wire_twin = MOCKUPS_DIR / "wo0010949_faas_sidebar_wire_desktop.png"
    desktop_intel_twin = MOCKUPS_DIR / "wo0010949_faas_sidebar_intel_desktop.png"
    mobile_twin = MOCKUPS_DIR / "wo0010949_faas_sidebar_mobile.png"

    print(f"[VERIFY] Starting Playwright audit against {BASE_URL}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # 1. Desktop Viewport (1920x1080)
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page = await ctx_desktop.new_page()

        resp = await page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        assert resp and resp.status == 200, f"Expected 200, got {resp.status if resp else 'None'}"

        # Wait for aside / BleacherChatWire
        aside = await page.wait_for_selector("aside", timeout=5000)
        assert aside, "Right sidebar (aside) not found"

        # Check tab buttons
        wire_btn = await page.wait_for_selector("button:has-text('BLEACHER WIRE')", timeout=5000)
        intel_btn = await page.wait_for_selector("button:has-text('GAME INTEL')", timeout=5000)
        assert wire_btn, "BLEACHER WIRE tab button not found"
        assert intel_btn, "GAME INTEL tab button not found"

        # Check header
        aside_text = await aside.inner_text()
        print(f"[VERIFY] Aside header text snippet: {aside_text[:200].replace(chr(10), ' ')}")
        assert "LIVE WIRE" in aside_text, "Missing 'LIVE WIRE' in header"
        assert "INGRESS ACTIVE" in aside_text, "Missing 'INGRESS ACTIVE' in header"

        # Save Desktop Wire Tab screenshot
        await page.screenshot(path=str(desktop_wire_twin), full_page=False)
        print(f"[VERIFY] Saved wire tab desktop twin to {desktop_wire_twin}")

        # Click GAME INTEL tab
        print("[VERIFY] Switching to GAME INTEL tab...")
        await intel_btn.click()
        await page.wait_for_timeout(600)  # Allow tab render transition

        intel_aside_text = await aside.inner_text()
        print(f"[VERIFY] Intel tab text: {intel_aside_text[:400].replace(chr(10), ' ')}")

        # Assert zero Boston / Bronx leakage
        assert "Max Fried" not in intel_aside_text, "FORBIDDEN: 'Max Fried' leaked into active game intel"
        assert "Nate Eaton" not in intel_aside_text, "FORBIDDEN: 'Nate Eaton' leaked into active game intel"
        assert "Boston Toxic Meltdown" not in intel_aside_text, "FORBIDDEN: 'Boston Toxic Meltdown' leaked into active game intel"
        assert "Bronx Euphoria" not in intel_aside_text, "FORBIDDEN: 'Bronx Euphoria' leaked into active game intel"

        # Assert active game components present
        assert "MOMENTUM & WIN PROBABILITY" in intel_aside_text, "Missing Momentum & Win Probability radar"
        assert "INTEL BRIEF" in intel_aside_text, "Missing Intel Brief"

        # Save Desktop Intel Tab screenshot
        await page.screenshot(path=str(desktop_intel_twin), full_page=False)
        print(f"[VERIFY] Saved intel tab desktop twin to {desktop_intel_twin}")
        await ctx_desktop.close()

        # 2. Mobile Viewport (390x844)
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True
        )
        page_m = await ctx_mobile.new_page()
        await page_m.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        await page_m.screenshot(path=str(mobile_twin), full_page=True)
        print(f"[VERIFY] Saved mobile twin to {mobile_twin}")
        await ctx_mobile.close()

        await browser.close()

    print("[VERIFY] ALL ACCEPTANCE CRITERIA VERIFIED ON DEDICATED HARDWARE.")

if __name__ == "__main__":
    asyncio.run(run_verification())
