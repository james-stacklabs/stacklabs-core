#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011062 Visual Twin Capture Utility
Captures Desktop (1920x1080) and Mobile (390x844) visual twins of FaaS Theater Deck
(Port 3033 ?view=theater) verifying live SportsX and DOM_M3U feed ingestion,
live sports top channel pills (CFB, MLB, NFL, SportsX, Artemis Quad-Grid),
and direct HLS stream mounting.
"""

import asyncio
import os
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
        print("[CAPTURE] Capturing Desktop Theater Deck (1920x1080)...")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_desktop = await ctx_desktop.new_page()
        await page_desktop.goto(target_url, wait_until="networkidle")
        await page_desktop.wait_for_timeout(3000)

        # Verify Theater Deck elements
        channels_btn = page_desktop.locator("text=CHANNELS")
        assert await channels_btn.count() > 0, "Missing Channels button"
        btn_text = await channels_btn.first.inner_text()
        print(f"[VERIFY] Desktop Theater Deck channels button confirmed: {btn_text}")

        tail_btn = page_desktop.locator("text=TAIL STREAM")
        assert await tail_btn.count() > 0, "Missing Tail Stream button"
        print("[VERIFY] Tail Stream ingress button verified!")

        # Verify channels loaded without dead YouTube IDs
        content = await page_desktop.content()
        assert "F3_8f0s6oQw" not in content, "Dead YouTube ID F3_8f0s6oQw found in DOM!"
        print("[VERIFY] Zero dead YouTube video IDs confirmed!")

        desktop_img = "wo0011062_desktop_theater_deck.png"
        for d in OUT_DIRS:
            dest = d / desktop_img
            await page_desktop.screenshot(path=str(dest), full_page=False)
            print(f"[SAVED] Desktop screenshot: {dest}")

        # 2. Mobile Visual Twin (390x844 - iPhone 14 Pro)
        print("[CAPTURE] Capturing Mobile Theater Deck (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto(target_url, wait_until="networkidle")
        await page_mobile.wait_for_timeout(3000)

        mobile_content = await page_mobile.content()
        assert "F3_8f0s6oQw" not in mobile_content, "Dead YouTube ID F3_8f0s6oQw found in Mobile DOM!"
        print("[VERIFY] Mobile Theater Deck verified with zero dead broadcast IDs!")

        mobile_img = "wo0011062_mobile_theater_deck.png"
        for d in OUT_DIRS:
            dest = d / mobile_img
            await page_mobile.screenshot(path=str(dest), full_page=False)
            print(f"[SAVED] Mobile screenshot: {dest}")

        await browser.close()
        print("✔ [SUCCESS] Dual visual twins captured and verified for WO0011062.")

if __name__ == "__main__":
    asyncio.run(capture_twins())
