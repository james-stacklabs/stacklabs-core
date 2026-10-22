#!/usr/bin/env python3
"""
WO0011042 Visual Twin Capture Utility
Captures Desktop (1920x1080) and Mobile (390x844) visual twins of CMDB Studio Port 3025
displaying the Live Shootout Arena, dual runner progress, and Institutional Proof Ledger.
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

    target_url = "http://127.0.0.1:3025/"

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

        # Verify Live Shootout Arena title
        arena_title = page_desktop.locator("text=Live Shootout Arena")
        assert await arena_title.count() > 0, "Missing Live Shootout Arena Header"

        # Click Launch Live Shootout
        launch_btn = page_desktop.locator("button:has-text('Launch Live Shootout')")
        if await launch_btn.count() > 0:
            print("[ACTION] Clicking 'Launch Live Shootout'...")
            await launch_btn.click()
            # Wait for shootout race to complete (VFS ~0.4s, SN ~5s)
            print("[WAIT] Waiting 6.5s for dual-runner shootout completion...")
            await page_desktop.wait_for_timeout(6500)

        # Verify Institutional Proof Ledger is visible
        ledger = page_desktop.locator("text=Institutional Shootout Proof & Parity Audit")
        assert await ledger.count() > 0, "Missing Institutional Proof Ledger"
        print("[VERIFY] Institutional Proof Ledger confirmed visible!")

        for d in OUT_DIRS:
            await page_desktop.screenshot(path=str(d / "wo0011042_shootout_arena_desktop.png"), full_page=False)
            await page_desktop.screenshot(path=str(d / "wo0011042_shootout_arena_desktop_full.png"), full_page=True)

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

        launch_btn_mobile = page_mobile.locator("button:has-text('Launch Live Shootout')")
        if await launch_btn_mobile.count() > 0:
            await launch_btn_mobile.click()
            await page_mobile.wait_for_timeout(6500)

        for d in OUT_DIRS:
            await page_mobile.screenshot(path=str(d / "wo0011042_shootout_arena_mobile.png"), full_page=False)

        await browser.close()
        print("[DONE] Visual Twins captured successfully.")

if __name__ == "__main__":
    asyncio.run(capture_twins())
