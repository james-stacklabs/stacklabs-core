#!/usr/bin/env python3
"""
StackLabs Retina Visual Twin Capture Utility for WO0011070
Captures 1920x1080 Desktop Twin and 390x844 Mobile Twin of Retina Quiet Luxury Default HUD.
Reference: WO0011070 | Invariant 15 (Two-Call Verification) | Invariant 26 (Gandalf UI Craft)
"""

import asyncio
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

EVIDENCE_DIR = Path("/home/james/stacklabs/evidence/visual_twins")
PILOT_DROPS_DIR = Path("/home/james/stacklabs/pilot_drops/screenshots")
ARTIFACT_DIR = Path("/home/james/.gemini/antigravity-cli/brain/722290fd-60cc-4575-a5ce-de68926179c1")

TARGET_URL = "http://127.0.0.1:3028/"

async def capture():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    PILOT_DROPS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop Visual Twin (1920x1080)
        print("[CAPTURE] Capturing Desktop Twin (1920x1080)...")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_desktop = await ctx_desktop.new_page()
        await page_desktop.goto(TARGET_URL, wait_until="domcontentloaded")
        await page_desktop.wait_for_timeout(1500)

        desktop_file = EVIDENCE_DIR / "retina_wo0011070_quiet_luxury_desktop.png"
        await page_desktop.screenshot(path=str(desktop_file), full_page=False)
        print(f"[OK] Desktop twin saved: {desktop_file}")

        shutil.copy2(desktop_file, PILOT_DROPS_DIR / "retina_wo0011070_quiet_luxury_desktop.png")
        shutil.copy2(desktop_file, ARTIFACT_DIR / "retina_wo0011070_quiet_luxury_desktop.png")
        await ctx_desktop.close()

        # 2. Mobile Visual Twin (390x844)
        print("[CAPTURE] Capturing Mobile Twin (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto(TARGET_URL, wait_until="domcontentloaded")
        await page_mobile.wait_for_timeout(1500)

        mobile_file = EVIDENCE_DIR / "retina_wo0011070_quiet_luxury_mobile.png"
        await page_mobile.screenshot(path=str(mobile_file), full_page=False)
        print(f"[OK] Mobile twin saved: {mobile_file}")

        shutil.copy2(mobile_file, PILOT_DROPS_DIR / "retina_wo0011070_quiet_luxury_mobile.png")
        shutil.copy2(mobile_file, ARTIFACT_DIR / "retina_wo0011070_quiet_luxury_mobile.png")
        await ctx_mobile.close()

        await browser.close()

    print("[SUCCESS] All visual twins captured successfully.")

if __name__ == "__main__":
    asyncio.run(capture())
