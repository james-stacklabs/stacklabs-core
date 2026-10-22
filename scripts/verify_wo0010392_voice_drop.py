#!/usr/bin/env python3
"""
Verification Script for WO0010392:
Mount Voice Problem Drop & Live Forge Burning Hot Beacon
Path: /home/james/stacklabs/scripts/verify_wo0010392_voice_drop.py
"""

import asyncio
import os
import shutil
from playwright.async_api import async_playwright

DESKTOP_OUT = "/home/james/sovereign_inbox/today/wo0010392_voice_drop_burning_hot_desktop.png"
MOBILE_OUT = "/home/james/sovereign_inbox/today/wo0010392_voice_drop_burning_hot_mobile.png"
ALIAS_OUT = "/home/james/sovereign_inbox/today/wo0010392_voice_drop_burning_hot.png"
URL = "https://localhost:3000/drop"

async def capture_views():
    os.makedirs(os.path.dirname(DESKTOP_OUT), exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Desktop Viewport (1440x900)
        print(f"[1/2] Capturing Desktop Viewport (1440x900) -> {DESKTOP_OUT}...")
        desktop_ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True
        )
        page_desktop = await desktop_ctx.new_page()
        await page_desktop.goto(URL, wait_until="networkidle")
        await page_desktop.wait_for_timeout(1500)
        
        content = await page_desktop.content()
        assert "Drop Your Business Bottleneck" in content, "Missing 'Drop Your Business Bottleneck' in content"
        assert "THE FORGE:" in content, "Missing 'THE FORGE:' in content"
        assert "BURNING HOT" in content, "Missing 'BURNING HOT' in content"
        
        await page_desktop.screenshot(path=DESKTOP_OUT, full_page=False)
        shutil.copyfile(DESKTOP_OUT, ALIAS_OUT)
        print(f"✔ Desktop screenshot saved ({os.path.getsize(DESKTOP_OUT):,} bytes)")
        await desktop_ctx.close()

        # 2. Mobile Viewport (390x844)
        print(f"[2/2] Capturing Mobile Viewport (390x844) -> {MOBILE_OUT}...")
        mobile_ctx = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            ignore_https_errors=True
        )
        page_mobile = await mobile_ctx.new_page()
        await page_mobile.goto(URL, wait_until="networkidle")
        await page_mobile.wait_for_timeout(1500)
        
        mobile_content = await page_mobile.content()
        assert "Drop Your Business Bottleneck" in mobile_content, "Missing 'Drop Your Business Bottleneck' in mobile content"
        assert "THE FORGE:" in mobile_content, "Missing 'THE FORGE:' in mobile content"
        assert "BURNING HOT" in mobile_content, "Missing 'BURNING HOT' in mobile content"
        
        await page_mobile.screenshot(path=MOBILE_OUT, full_page=False)
        print(f"✔ Mobile screenshot saved ({os.path.getsize(MOBILE_OUT):,} bytes)")
        await mobile_ctx.close()

        await browser.close()

    print("\n✅ Verification PASSED: All visual twins captured and assertions validated.")

if __name__ == "__main__":
    asyncio.run(capture_views())
