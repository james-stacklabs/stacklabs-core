#!/usr/bin/env python3
"""
WO0011007 Visual Twin Capture Utility
Captures Desktop (1920x1080) and Mobile (390x844) visual twins of Pegasus Bedroom Theater Deck.
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

    target_url = "http://127.0.0.1:3033/?view=theater"

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
        await page_desktop.wait_for_timeout(1500)

        # Verify key elements
        assert await page_desktop.locator("text=[NODE: PEGASUS-DECK-01]").count() > 0, "Missing node header"
        assert await page_desktop.locator("text=[STATUS: MESH_ONLINE]").count() > 0, "Missing status badge"
        assert await page_desktop.locator("text=[TNF: DAL @ TB]").count() > 0, "Missing TNF preset pill"
        assert await page_desktop.locator("text=LOAD FEED ↵").count() > 0, "Missing load feed button"

        for d in OUT_DIRS:
            await page_desktop.screenshot(path=str(d / "wo0011007_theater_deck_desktop.png"), full_page=False)

        # 2. Mobile Visual Twin (390x844)
        print("[CAPTURE] Capturing Mobile Twin (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto(target_url, wait_until="networkidle")
        await page_mobile.wait_for_timeout(1500)

        for d in OUT_DIRS:
            await page_mobile.screenshot(path=str(d / "wo0011007_theater_deck_mobile.png"), full_page=False)

        await browser.close()
        print("[DONE] Visual Twins captured successfully.")

if __name__ == "__main__":
    asyncio.run(capture_twins())
