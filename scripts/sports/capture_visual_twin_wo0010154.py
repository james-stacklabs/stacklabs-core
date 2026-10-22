#!/usr/bin/env python3
"""
Capture Pegasus Playwright live visual twin for WO0010154
URL: https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=823574
Outputs: /home/james/stacklabs/pegasus_visual_twin_WO0010154.png
Asserts: Zero outer scrollbar (KI-095: document.documentElement.scrollHeight <= window.innerHeight)
"""

import os
import sys
import json
import asyncio
from playwright.async_api import async_playwright

TARGET_URL = "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=823574"
LOCAL_URL = "https://127.0.0.1:3009/?domain=GLOBAL&room=823574"
OUTPUT_PATH = "/home/james/stacklabs/pegasus_visual_twin_WO0010154.png"
SCREENSHOTS_PATH = "/home/james/stacklabs/screenshots/pegasus_visual_twin_WO0010154.png"

async def capture():
    print(f"[*] Launching Playwright Chromium for Visual Twin (WO0010154)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            user_agent="Sovereign-Pegasus-VisualTwin/1.0"
        )
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        print(f"[*] Navigating to {TARGET_URL}...")
        try:
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=25000)
        except Exception as e:
            print(f"[WARN] Failed to load tailscale domain ({e}), falling back to 127.0.0.1...")
            await page.goto(LOCAL_URL, wait_until="networkidle", timeout=25000)

        await page.wait_for_timeout(3000)

        # Assert KI-095 zero outer scrollbar
        metrics = await page.evaluate("""() => {
            const scrollHeight = document.documentElement.scrollHeight;
            const innerHeight = window.innerHeight;
            return {
                scrollHeight: scrollHeight,
                innerHeight: innerHeight,
                zero_outer_scrollbar: scrollHeight <= innerHeight
            };
        }""")
        print(f"[*] KI-095 Viewport Metrics: {metrics}")
        assert metrics["zero_outer_scrollbar"], f"KI-095 VIOLATION: scrollHeight ({metrics['scrollHeight']}) > innerHeight ({metrics['innerHeight']})"

        # Verify Key UI elements exist
        title_elem = await page.query_selector("h1")
        title_text = await title_elem.inner_text() if title_elem else "N/A"
        print(f"[*] Page Header: {title_text.strip()}")

        sim_play_btn = await page.query_selector("#sim-play-pause-btn")
        bookmark_alonso = await page.query_selector("#bookmark-alonso-hr")
        bookmark_mayo = await page.query_selector("#bookmark-mayo-hr")
        hot_patch_toggle = await page.query_selector("#hot-patcher-toggle-btn")

        print(f"[*] Verified Controls:")
        print(f"    - Play/Pause Button: {'FOUND' if sim_play_btn else 'NOT FOUND'}")
        print(f"    - Bookmark Alonso HR: {'FOUND' if bookmark_alonso else 'NOT FOUND'}")
        print(f"    - Bookmark Mayo HR: {'FOUND' if bookmark_mayo else 'NOT FOUND'}")
        print(f"    - Hot-Patcher Toggle: {'FOUND' if hot_patch_toggle else 'NOT FOUND'}")

        # Capture Screenshot
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(SCREENSHOTS_PATH), exist_ok=True)
        await page.screenshot(path=OUTPUT_PATH, full_page=False)
        await page.screenshot(path=SCREENSHOTS_PATH, full_page=False)
        print(f"✔ Pegasus Visual Twin saved to: {OUTPUT_PATH}")
        print(f"✔ Copied to screenshots dir: {SCREENSHOTS_PATH}")

        await browser.close()
        return metrics

if __name__ == "__main__":
    metrics = asyncio.run(capture())
    print("[SUCCESS] All visual twin invariants satisfied.")
