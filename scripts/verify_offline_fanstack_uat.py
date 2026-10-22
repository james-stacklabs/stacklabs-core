#!/usr/bin/env python3
"""
Live Playwright Visual UAT Script
Ticket: ENHC0010008-OFFLINE-HISTORICAL-CORPUS-ADVOCATE-ENGINE
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOT_PATH = Path("/home/james/sovereign_inbox/tickets/ENHC0010008-OFFLINE-HISTORICAL-CORPUS-ADVOCATE-ENGINE/mockups/playwright_live_fanstack.png")

async def run_visual_uat():
    print("🌐 Launching Playwright browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors", "--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True
        )
        page = await context.new_page()

        url = "https://127.0.0.1:3009/"
        print(f"Navigating to {url}...")
        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
        except Exception as e:
            print(f"Navigation fallback: {e}")
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        await asyncio.sleep(2.0)

        SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
        print(f"📸 Saved live visual UAT screenshot to: {SCREENSHOT_PATH}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_visual_uat())
