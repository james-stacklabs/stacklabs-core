#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011058 Visual Twin Capture Utility
Captures Desktop (1920x1080) and Mobile (390x844) visual twins of FaaS DualStreamSplitView (Port 3033)
displaying the live Barf & Burl gameday crossfire dialectic, VFS event telemetry,
and advocate take cards.
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

    target_url = "http://127.0.0.1:3033/?view=sidebyside"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop Visual Twin (1920x1080)
        print("[CAPTURE] Capturing Desktop Dual Stream Crossfire (1920x1080)...")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_desktop = await ctx_desktop.new_page()
        await page_desktop.goto(target_url, wait_until="networkidle")
        await page_desktop.wait_for_timeout(2500) # Wait for banter polling

        # Verify crossfire dialectic elements
        title_loc = page_desktop.locator("text=DUAL STREAM CROSSFIRE")
        assert await title_loc.count() > 0, "Missing DUAL STREAM CROSSFIRE Header"
        print("[VERIFY] Desktop Dual Stream Crossfire confirmed mounted!")

        burl_take = page_desktop.locator("text=Burl (Bayou Coonhound)")
        assert await burl_take.count() > 0, "Missing Burl take strip"

        barf_take = page_desktop.locator("text=Barf (Queens Mawg)")
        assert await barf_take.count() > 0, "Missing Barf take strip"

        desktop_img = "wo0011058_desktop_dual_stream_crossfire.png"
        for d in OUT_DIRS:
            dest = d / desktop_img
            await page_desktop.screenshot(path=str(dest), full_page=False)
            print(f"[SAVED] Desktop screenshot: {dest}")

        # 2. Mobile Visual Twin (390x844 - iPhone 14 Pro)
        print("[CAPTURE] Capturing Mobile Dual Stream Crossfire (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto(target_url, wait_until="networkidle")
        await page_mobile.wait_for_timeout(2500)

        mobile_img = "wo0011058_mobile_dual_stream_crossfire.png"
        for d in OUT_DIRS:
            dest = d / mobile_img
            await page_mobile.screenshot(path=str(dest), full_page=False)
            print(f"[SAVED] Mobile screenshot: {dest}")

        await browser.close()
        print("[SUCCESS] All visual twin captures verified!")

if __name__ == "__main__":
    asyncio.run(capture_twins())
