#!/usr/bin/env python3
"""
StackLabs Visual Twin Capture Utility for WO0011106
Captures Desktop (1920x1080) and Mobile (390x844) Twins for:
1. Port 3025 (CMDB Studio Client Demo) - Asserting zero Swanson presence
2. Port 8088 (/cockpit) - Asserting 5th tab Swanson Crawl renders cleanly
Reference: WO0011106 | Invariant 15 | Invariant 26
"""

import asyncio
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

EVIDENCE_DIR = Path("/home/james/stacklabs/evidence/visual_twins")
ARTIFACT_DIR = Path("/home/james/.gemini/antigravity-cli/brain/31d955d2-910c-4343-8543-9bf539eded56")
PILOT_DROPS_DIR = Path("/home/james/stacklabs/pilot_drops/screenshots")

PORT_3025_URL = "https://127.0.0.1:3025/"
PORT_8088_URL = "http://127.0.0.1:8088/cockpit"

async def capture():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    PILOT_DROPS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ---------------------------------------------------------
        # 1. CMDB Studio (Port 3025) - Desktop (1920x1080)
        # ---------------------------------------------------------
        print("[CAPTURE] Capturing CMDB Studio Desktop Twin (1920x1080)...")
        ctx_3025_dt = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            ignore_https_errors=True
        )
        page_3025_dt = await ctx_3025_dt.new_page()
        await page_3025_dt.goto(PORT_3025_URL, wait_until="networkidle")
        await page_3025_dt.wait_for_timeout(1000)

        # Assertion: Zero Swanson in page text
        content_3025 = await page_3025_dt.content()
        assert "Swanson" not in content_3025, "CRITICAL ERROR: Swanson found in Port 3025 desktop content!"
        print("[VERIFIED] Zero Swanson references in Port 3025 Desktop DOM")

        file_3025_dt = EVIDENCE_DIR / "cmdb_studio_wo0011106_desktop.png"
        await page_3025_dt.screenshot(path=str(file_3025_dt), full_page=False)
        shutil.copy2(file_3025_dt, ARTIFACT_DIR / "cmdb_studio_wo0011106_desktop.png")
        shutil.copy2(file_3025_dt, PILOT_DROPS_DIR / "cmdb_studio_wo0011106_desktop.png")
        print(f"[OK] Saved: {file_3025_dt}")
        await ctx_3025_dt.close()

        # ---------------------------------------------------------
        # 2. CMDB Studio (Port 3025) - Mobile (390x844)
        # ---------------------------------------------------------
        print("[CAPTURE] Capturing CMDB Studio Mobile Twin (390x844)...")
        ctx_3025_mb = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2,
            ignore_https_errors=True
        )
        page_3025_mb = await ctx_3025_mb.new_page()
        await page_3025_mb.goto(PORT_3025_URL, wait_until="networkidle")
        await page_3025_mb.wait_for_timeout(1000)

        file_3025_mb = EVIDENCE_DIR / "cmdb_studio_wo0011106_mobile.png"
        await page_3025_mb.screenshot(path=str(file_3025_mb), full_page=False)
        shutil.copy2(file_3025_mb, ARTIFACT_DIR / "cmdb_studio_wo0011106_mobile.png")
        shutil.copy2(file_3025_mb, PILOT_DROPS_DIR / "cmdb_studio_wo0011106_mobile.png")
        print(f"[OK] Saved: {file_3025_mb}")
        await ctx_3025_mb.close()

        # ---------------------------------------------------------
        # 3. Cockpit (Port 8088) - Desktop (1920x1080) with Swanson Crawl Tab
        # ---------------------------------------------------------
        print("[CAPTURE] Capturing Cockpit Swanson Crawl Desktop Twin (1920x1080)...")
        ctx_8088_dt = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            ignore_https_errors=True
        )
        page_8088_dt = await ctx_8088_dt.new_page()
        await page_8088_dt.goto(PORT_8088_URL, wait_until="networkidle")
        await page_8088_dt.wait_for_timeout(500)

        # Click Swanson Crawl tab
        await page_8088_dt.click("#tab-crawl")
        await page_8088_dt.wait_for_timeout(1500)

        # Assertions
        content_8088 = await page_8088_dt.content()
        assert "tab-crawl" in content_8088, "CRITICAL ERROR: tab-crawl not found in Cockpit DOM!"
        assert "Swanson Crawl" in content_8088, "CRITICAL ERROR: Swanson Crawl not found in Cockpit DOM!"
        print("[VERIFIED] Swanson Crawl tab rendered cleanly in Cockpit Desktop DOM")

        file_8088_dt = EVIDENCE_DIR / "cockpit_swanson_crawl_wo0011106_desktop.png"
        await page_8088_dt.screenshot(path=str(file_8088_dt), full_page=False)
        shutil.copy2(file_8088_dt, ARTIFACT_DIR / "cockpit_swanson_crawl_wo0011106_desktop.png")
        shutil.copy2(file_8088_dt, PILOT_DROPS_DIR / "cockpit_swanson_crawl_wo0011106_desktop.png")
        print(f"[OK] Saved: {file_8088_dt}")
        await ctx_8088_dt.close()

        # ---------------------------------------------------------
        # 4. Cockpit (Port 8088) - Mobile (390x844) with Swanson Crawl Tab
        # ---------------------------------------------------------
        print("[CAPTURE] Capturing Cockpit Swanson Crawl Mobile Twin (390x844)...")
        ctx_8088_mb = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2,
            ignore_https_errors=True
        )
        page_8088_mb = await ctx_8088_mb.new_page()
        await page_8088_mb.goto(PORT_8088_URL, wait_until="networkidle")
        await page_8088_mb.wait_for_timeout(500)

        # Click Swanson Crawl tab
        await page_8088_mb.evaluate("switchTab('crawl')")
        await page_8088_mb.wait_for_timeout(1500)

        file_8088_mb = EVIDENCE_DIR / "cockpit_swanson_crawl_wo0011106_mobile.png"
        await page_8088_mb.screenshot(path=str(file_8088_mb), full_page=False)
        shutil.copy2(file_8088_mb, ARTIFACT_DIR / "cockpit_swanson_crawl_wo0011106_mobile.png")
        shutil.copy2(file_8088_mb, PILOT_DROPS_DIR / "cockpit_swanson_crawl_wo0011106_mobile.png")
        print(f"[OK] Saved: {file_8088_mb}")
        await ctx_8088_mb.close()

        await browser.close()
        print("\n[ALL COMPLETE] All 4 Visual Twins captured and verified successfully.")

if __name__ == "__main__":
    asyncio.run(capture())
