#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011059 Visual Twin Capture Utility
Captures Desktop (1920x1080) and Mobile (390x844) visual twins of FaaS Predict Exchange (Port 3033 / ?view=predict)
displaying live advocate bankrolls (enrolling Burl alongside Barf, Sammy, Brenda),
stadium weather barometrics, dynamic contracts, and filled order tickets.
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

    target_url = "http://127.0.0.1:3033/?view=predict"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop Visual Twin (1920x1080)
        print("[CAPTURE] Capturing Desktop Predict Exchange (1920x1080)...")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_desktop = await ctx_desktop.new_page()
        await page_desktop.goto(target_url, wait_until="networkidle")
        await page_desktop.wait_for_timeout(3500) # Wait for live 3s polling

        # Verify Predict Exchange elements
        title_loc = page_desktop.locator("text=THE SOVEREIGN SYNDICATE // LOCAL PREDICT EXCHANGE")
        assert await title_loc.count() > 0, "Missing Predict Exchange Header"
        print("[VERIFY] Desktop Predict Exchange header confirmed mounted!")

        burl_adv = page_desktop.locator("text=Burl (Bayou Coonhound)")
        assert await burl_adv.count() > 0, "Missing Burl advocate card"
        print("[VERIFY] Burl (@burl_bayou) bankroll card verified!")

        barf_adv = page_desktop.locator("text=Barf (Queens Mawg)")
        assert await barf_adv.count() > 0, "Missing Barf advocate card"

        sammy_adv = page_desktop.locator("text=Sammy The Savant")
        assert await sammy_adv.count() > 0, "Missing Sammy advocate card"

        brenda_adv = page_desktop.locator("text=Brenda Bombshell")
        assert await brenda_adv.count() > 0, "Missing Brenda advocate card"

        # Verify Weather Barometrics
        weather_loc = page_desktop.locator("text=Live Stadium Weather Barometrics")
        assert await weather_loc.count() > 0, "Missing Weather Barometrics ribbon"
        print("[VERIFY] Weather barometrics feed verified!")

        desktop_img = "wo0011059_desktop_predict_exchange.png"
        for d in OUT_DIRS:
            dest = d / desktop_img
            await page_desktop.screenshot(path=str(dest), full_page=False)
            print(f"[SAVED] Desktop screenshot: {dest}")

        # 2. Mobile Visual Twin (390x844 - iPhone 14 Pro)
        print("[CAPTURE] Capturing Mobile Predict Exchange (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto(target_url, wait_until="networkidle")
        await page_mobile.wait_for_timeout(3500)

        # Verify core mobile components
        assert await page_mobile.locator("text=Burl (Bayou Coonhound)").count() > 0, "Missing Burl on mobile viewport"
        print("[VERIFY] Mobile Predict Exchange confirmed mounted!")

        mobile_img = "wo0011059_mobile_predict_exchange.png"
        for d in OUT_DIRS:
            dest = d / mobile_img
            await page_mobile.screenshot(path=str(dest), full_page=False)
            print(f"[SAVED] Mobile screenshot: {dest}")

        await browser.close()
        print("✔ [SUCCESS] Dual visual twins captured and verified for WO0011059.")

if __name__ == "__main__":
    asyncio.run(capture_twins())
