#!/usr/bin/env python3
"""
WO0011009 Visual Twin Capture Utility
Captures Desktop (1920x1080) and Mobile (390x844) visual twins of FaaS Slate Ribbon displaying stadium zip codes and roof pills.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT_DIRS = [
    Path("/home/james/stacklabs/walkthroughs/screenshots"),
    Path("/home/james/stacklabs/pilot_drops/screenshots"),
]

async def capture_twins():
    for d in OUT_DIRS:
        d.mkdir(parents=True, exist_ok=True)

    target_url = "http://127.0.0.1:3033/?pin=1996&view=gameroom"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop Visual Twin (1920x1080)
        print("[CAPTURE] Capturing Desktop Twin (1920x1080)...")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_desktop = await ctx_desktop.new_page()
        await page_desktop.goto(target_url, wait_until="networkidle")
        await page_desktop.wait_for_timeout(2000)

        # Verify key elements
        ribbon = page_desktop.locator("div:has-text('ALL FEEDS')")
        assert await ribbon.count() > 0, "Missing SlateSwitcherRibbon"

        # Check for stadium zip badge (e.g., [98195] or similar zip code badge)
        zip_badges = await page_desktop.locator("span[title*='•']").all_text_contents()
        print(f"[VERIFY] Found {len(zip_badges)} stadium zip badges: {zip_badges[:5]}")

        for d in OUT_DIRS:
            await page_desktop.screenshot(path=str(d / "wo0011009_slate_ribbon_stadium_zip_desktop.png"), full_page=False)

        # 2. Mobile Visual Twin (390x844)
        print("[CAPTURE] Capturing Mobile Twin (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto(target_url, wait_until="networkidle")
        await page_mobile.wait_for_timeout(2000)

        for d in OUT_DIRS:
            await page_mobile.screenshot(path=str(d / "wo0011009_slate_ribbon_stadium_zip_mobile.png"), full_page=False)

        await browser.close()
        print("[DONE] Visual Twins captured successfully.")

if __name__ == "__main__":
    asyncio.run(capture_twins())
