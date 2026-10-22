#!/usr/bin/env python3
"""
scripts/verify_wo0010537_queue_decoupling.py
Playwright Visual Twin Capture & Verification for WO0010537:
Decouple Work Order Stage Dropzone to Dedicated Tab on Founder Cockpit (Port 8088).
Captures:
1. pegasus_uat_wo0010537_queue_hud.png (1920x1080)
2. pegasus_uat_wo0010537_stage_wo.png (1920x1080)
Copies to /home/james/sovereign_inbox/today/
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8088/cockpit"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")
TODAY_DIR = Path("/home/james/sovereign_inbox/today")

async def main():
    MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
    TODAY_DIR.mkdir(parents=True, exist_ok=True)

    queue_hud_png = MOCKUPS_DIR / "pegasus_uat_wo0010537_queue_hud.png"
    stage_wo_png = MOCKUPS_DIR / "pegasus_uat_wo0010537_stage_wo.png"

    print("[PLAYWRIGHT] Launching Chromium headless on Clio metal...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page = await ctx.new_page()

        print(f"[PLAYWRIGHT] Navigating to {BASE_URL}...")
        resp = await page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        assert resp.status == 200, f"Expected 200 OK, got {resp.status}"

        # -------------------------------------------------------------
        # 1. VERIFY QUEUE HUD TAB (ZERO-SCROLL)
        # -------------------------------------------------------------
        print("[PLAYWRIGHT] Clicking #btn-queue...")
        await page.click("#btn-queue")
        await page.wait_for_timeout(600)

        # Assert #tab-queue is visible
        is_queue_visible = await page.evaluate("!document.getElementById('tab-queue').classList.contains('hidden')")
        assert is_queue_visible, "Tab #tab-queue must be visible!"

        # Assert #queue-incoming-count is visible
        incoming_visible = await page.is_visible("#queue-incoming-count")
        assert incoming_visible, "#queue-incoming-count must be visible!"

        # Assert bounding box of #queue-incoming-count is near top (zero scroll)
        box = await page.locator("#queue-incoming-count").bounding_box()
        assert box is not None, "Bounding box for #queue-incoming-count is None"
        print(f"[PLAYWRIGHT] #queue-incoming-count y-coordinate: {box['y']}px (Must be < 300px for zero-scroll HUD)")
        assert box['y'] < 300, f"Expected queue incoming count to be above 300px, got {box['y']}"

        # Assert shortcut button to stage exists
        shortcut_btn = await page.query_selector("button:has-text('Stage New Work Order')")
        assert shortcut_btn is not None, "'Stage New Work Order' shortcut button must exist in #tab-queue"

        # Capture Desktop Queue HUD Visual Twin
        print(f"[PLAYWRIGHT] Capturing Queue HUD Twin -> {queue_hud_png}")
        await page.screenshot(path=str(queue_hud_png), full_page=False)
        shutil.copy(queue_hud_png, TODAY_DIR / queue_hud_png.name)

        # -------------------------------------------------------------
        # 2. VERIFY DEDICATED STAGE WO TAB
        # -------------------------------------------------------------
        print("[PLAYWRIGHT] Clicking #btn-stage...")
        await page.click("#btn-stage")
        await page.wait_for_timeout(600)

        # Assert #tab-stage is visible
        is_stage_visible = await page.evaluate("!document.getElementById('tab-stage').classList.contains('hidden')")
        assert is_stage_visible, "Tab #tab-stage must be visible!"

        # Assert #stage-wo-content is visible
        is_content_visible = await page.is_visible("#stage-wo-content")
        assert is_content_visible, "#stage-wo-content textarea must be visible!"

        # Assert #tab-queue is now hidden
        is_queue_hidden = await page.evaluate("document.getElementById('tab-queue').classList.contains('hidden')")
        assert is_queue_hidden, "Tab #tab-queue must be hidden when tab-stage is active!"

        # Assert back button to queue exists
        back_btn = await page.query_selector("button:has-text('← View Queue')")
        assert back_btn is not None, "'← View Queue' back button must exist in #tab-stage"

        # Capture Desktop Stage WO Visual Twin
        print(f"[PLAYWRIGHT] Capturing Stage WO Twin -> {stage_wo_png}")
        await page.screenshot(path=str(stage_wo_png), full_page=False)
        shutil.copy(stage_wo_png, TODAY_DIR / stage_wo_png.name)

        # -------------------------------------------------------------
        # 3. TEST SHORTCUT BUTTONS INTERACTION
        # -------------------------------------------------------------
        print("[PLAYWRIGHT] Testing shortcut button: click '← View Queue'...")
        await page.click("button:has-text('← View Queue')")
        await page.wait_for_timeout(400)
        assert await page.evaluate("!document.getElementById('tab-queue').classList.contains('hidden')"), "← View Queue should switch back to #tab-queue"

        print("[PLAYWRIGHT] Testing shortcut button: click 'Stage New Work Order'...")
        await page.click("button:has-text('Stage New Work Order')")
        await page.wait_for_timeout(400)
        assert await page.evaluate("!document.getElementById('tab-stage').classList.contains('hidden')"), "Stage New Work Order should switch to #tab-stage"

        await browser.close()

    print("[PLAYWRIGHT] ✓ All Playwright verifications passed successfully!")
    print(f"[PLAYWRIGHT] Twins saved to {queue_hud_png} and {stage_wo_png}")
    print(f"[PLAYWRIGHT] Copied twins to {TODAY_DIR}")

if __name__ == "__main__":
    asyncio.run(main())
