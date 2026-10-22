#!/usr/bin/env python3
"""
StackLabs CMDB Studio Visual Twin Capture Utility for WO0011102
Captures 1920x1080 Desktop Twin, 1280x800 Laptop Twin, and 390x844 Mobile Twin
Verifying the scrubbed institutional terminology and de-janked header navigation.
Reference: WO0011102 | Invariant 15 (Two-Call Verification) | Invariant 26 (Gandalf UI Craft)
"""

import asyncio
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

EVIDENCE_DIR = Path("/home/james/stacklabs/evidence/visual_twins")
ARTIFACT_DIR = Path("/home/james/.gemini/antigravity-cli/brain/986232a8-c94b-49d9-bce2-927933168900")
PILOT_DROPS_DIR = Path("/home/james/stacklabs/pilot_drops/screenshots")

TARGET_URL = "https://127.0.0.1:3025/"

async def capture():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    PILOT_DROPS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop Visual Twin (1920x1080)
        print("[CAPTURE] Capturing Desktop Twin (1920x1080)...")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            ignore_https_errors=True
        )
        page_desktop = await ctx_desktop.new_page()
        await page_desktop.goto(TARGET_URL, wait_until="networkidle")
        await page_desktop.wait_for_timeout(1000)

        desktop_file = EVIDENCE_DIR / "cmdb_studio_wo0011102_desktop.png"
        await page_desktop.screenshot(path=str(desktop_file), full_page=False)
        print(f"[OK] Desktop twin saved: {desktop_file}")
        shutil.copy2(desktop_file, ARTIFACT_DIR / "cmdb_studio_wo0011102_desktop.png")
        shutil.copy2(desktop_file, PILOT_DROPS_DIR / "cmdb_studio_wo0011102_desktop.png")
        await ctx_desktop.close()

        # 2. Laptop Visual Twin (1280x800)
        print("[CAPTURE] Capturing Laptop Twin (1280x800)...")
        ctx_laptop = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
            ignore_https_errors=True
        )
        page_laptop = await ctx_laptop.new_page()
        await page_laptop.goto(TARGET_URL, wait_until="networkidle")
        await page_laptop.wait_for_timeout(1000)

        laptop_file = EVIDENCE_DIR / "cmdb_studio_wo0011102_laptop.png"
        await page_laptop.screenshot(path=str(laptop_file), full_page=False)
        print(f"[OK] Laptop twin saved: {laptop_file}")
        shutil.copy2(laptop_file, ARTIFACT_DIR / "cmdb_studio_wo0011102_laptop.png")
        shutil.copy2(laptop_file, PILOT_DROPS_DIR / "cmdb_studio_wo0011102_laptop.png")
        await ctx_laptop.close()

        # 3. Mobile Visual Twin (390x844)
        print("[CAPTURE] Capturing Mobile Twin (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2,
            ignore_https_errors=True
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto(TARGET_URL, wait_until="networkidle")
        await page_mobile.wait_for_timeout(1000)

        mobile_file = EVIDENCE_DIR / "cmdb_studio_wo0011102_mobile.png"
        await page_mobile.screenshot(path=str(mobile_file), full_page=False)
        print(f"[OK] Mobile twin saved: {mobile_file}")
        shutil.copy2(mobile_file, ARTIFACT_DIR / "cmdb_studio_wo0011102_mobile.png")
        shutil.copy2(mobile_file, PILOT_DROPS_DIR / "cmdb_studio_wo0011102_mobile.png")
        await ctx_mobile.close()

        await browser.close()
        print("[ALL COMPLETE] All visual twins captured and staged.")

if __name__ == "__main__":
    asyncio.run(capture())
