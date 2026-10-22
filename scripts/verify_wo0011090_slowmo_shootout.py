#!/usr/bin/env python3
"""
StackLabs WO0011090 Visual Twin & Functional Verification Script
Path: /home/james/stacklabs/scripts/verify_wo0011090_slowmo_shootout.py
Author: James Carroll (Pilot), Lead Systems Architect
Host: Clio Bare Metal (Beelink SER Mini PC, AMD Ryzen 7 7735HS)
"""

import os
import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:3025/#slowmo"
EVIDENCE_DIR = Path("/home/james/stacklabs/evidence/visual_twins")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP_SCREENSHOT = EVIDENCE_DIR / "WO0011090_slowmo_desktop.png"
MOBILE_SCREENSHOT = EVIDENCE_DIR / "WO0011090_slowmo_mobile.png"


async def run_verification():
    print(f"[VERIFY PLAYWRIGHT] Launching browser against {BASE_URL}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # 1. Desktop Viewport (1920x1080)
        print("\n--- 1. Desktop Viewport (1920x1080) ---")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_d = await ctx_desktop.new_page()

        resp = await page_d.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        print(f"Page loaded: HTTP {resp.status if resp else 'N/A'}")

        # Assert warning notice banner is present
        banner = await page_d.wait_for_selector("text=Artificial 1,000x Slow-Motion Engaged", timeout=8000)
        assert banner, "Warning notice banner not found!"
        print("✔ Found warning notice banner")

        # Click Trigger Shootout
        trigger_btn = await page_d.wait_for_selector("text=TRIGGER SHOOTOUT", timeout=5000)
        assert trigger_btn, "TRIGGER SHOOTOUT button not found!"
        print("Clicking 'TRIGGER SHOOTOUT' button...")
        await trigger_btn.click()

        # Wait for root cause lock
        root_badge = await page_d.wait_for_selector("text=ROOT CAUSE: pod_01_sw_01", timeout=5000)
        assert root_badge, "Root cause badge not found after shootout run!"
        print("✔ Root cause confirmed locked")

        await page_d.screenshot(path=str(DESKTOP_SCREENSHOT), full_page=True)
        print(f"✔ Desktop visual twin saved: {DESKTOP_SCREENSHOT}")

        # 2. Mobile Viewport (390x844)
        print("\n--- 2. Mobile Viewport (390x844) ---")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True
        )
        page_m = await ctx_mobile.new_page()

        await page_m.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        await page_m.screenshot(path=str(MOBILE_SCREENSHOT), full_page=True)
        print(f"✔ Mobile visual twin saved: {MOBILE_SCREENSHOT}")

        await browser.close()
        print("\n🏆 WO0011090 Verification Complete!")


if __name__ == "__main__":
    asyncio.run(run_verification())
