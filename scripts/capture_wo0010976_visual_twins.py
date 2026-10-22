#!/usr/bin/env python3
"""
WO0010976 Visual Twin Capture Utility
Captures Desktop (1920x1080) and Mobile (390x844) visual twins of Daily Barf Advocate Crossfire.
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

    target_url = "http://127.0.0.1:3033/?view=mobile&tab=barf"

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
        await page_desktop.wait_for_timeout(1000)

        # Scroll to crossfire section
        crossfire_elem = page_desktop.locator("text=ADVOCATE WIRE // COWBOYS VS BARF")
        if await crossfire_elem.count() > 0:
            await crossfire_elem.scroll_into_view_if_needed()
            await page_desktop.wait_for_timeout(500)

        for d in OUT_DIRS:
            await page_desktop.screenshot(path=str(d / "wo0010976_barf_crossfire_desktop.png"), full_page=False)
            await page_desktop.screenshot(path=str(d / "wo0010976_barf_crossfire_desktop_full.png"), full_page=True)

        # 2. Mobile Visual Twin (390x844)
        print("[CAPTURE] Capturing Mobile Twin (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto(target_url, wait_until="networkidle")
        await page_mobile.wait_for_timeout(1000)

        crossfire_elem_mobile = page_mobile.locator("text=ADVOCATE WIRE // COWBOYS VS BARF")
        if await crossfire_elem_mobile.count() > 0:
            await crossfire_elem_mobile.scroll_into_view_if_needed()
            await page_mobile.wait_for_timeout(500)

        for d in OUT_DIRS:
            await page_mobile.screenshot(path=str(d / "wo0010976_barf_crossfire_mobile.png"), full_page=False)
            await page_mobile.screenshot(path=str(d / "wo0010976_barf_crossfire_mobile_full.png"), full_page=True)

        await browser.close()
        print("[DONE] Visual Twins captured successfully.")

if __name__ == "__main__":
    asyncio.run(capture_twins())
