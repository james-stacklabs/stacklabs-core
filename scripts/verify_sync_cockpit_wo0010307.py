#!/usr/bin/env python3
"""
Playwright Verification & Visual Twin Capture for WO0010307:
Overhaul Sovereign Sync Cockpit (Tool #43) with Multi-Envelope NotebookLM Workflow.
"""

import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def verify_and_capture():
    url = "http://127.0.0.1:8088/sync"
    output_image = "/home/james/stacklabs/pegasus_visual_twin_WO0010307_sync_cockpit.png"
    
    print(f"[PLAYWRIGHT] Launching browser to test {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2
        )
        page = await context.new_page()

        print(f"[PLAYWRIGHT] Navigating to {url}...")
        response = await page.goto(url, wait_until="networkidle", timeout=15000)
        assert response.status == 200, f"Expected 200 OK, got {response.status}"

        # 1. Assert Title and Header
        title = await page.title()
        print(f"[PLAYWRIGHT] Page title: {title}")
        assert "Sovereign Sync Cockpit" in title

        # Wait for envelopes to render
        await page.wait_for_selector(".envelope-pill", timeout=5000)
        pills = await page.locator(".envelope-pill").all()
        print(f"[PLAYWRIGHT] Detected {len(pills)} envelope pills:")
        for pill in pills:
            text = (await pill.inner_text()).replace("\n", " ")
            print(f"  - {text}")
        assert len(pills) == 6, f"Expected 6 envelope pills, found {len(pills)}"

        # 2. Check 07 Johnny Carroll active state
        badge_text = await page.locator("#activeEnvelopeBadge").inner_text()
        print(f"[PLAYWRIGHT] Active envelope badge: {badge_text}")
        assert "Johnny Carroll" in badge_text

        # 3. Click 06 Davidson Malone pill to test envelope switching
        dm_pill = page.locator(".envelope-pill[data-key='06_Davidson_Malone_Prospectus']")
        await dm_pill.click()
        await page.wait_for_timeout(1000)

        dm_badge = await page.locator("#activeEnvelopeBadge").inner_text()
        print(f"[PLAYWRIGHT] After switch, active badge: {dm_badge}")
        assert "Davidson Malone" in dm_badge

        # Check clutter alert banner on Davidson Malone
        clutter_alert = page.locator("#clutterAlert")
        is_visible = await clutter_alert.is_visible()
        print(f"[PLAYWRIGHT] Clutter alert visible for Davidson Malone: {is_visible}")
        assert is_visible, "Expected clutter alert to be visible for 06_Davidson_Malone_Prospectus"

        clutter_text = await page.locator("#clutterCountText").inner_text()
        print(f"[PLAYWRIGHT] Clutter count text: {clutter_text}")
        assert "1 non-source file" in clutter_text

        # 4. Switch back to 07 Johnny Carroll
        jc_pill = page.locator(".envelope-pill[data-key='07_JohnnyCarroll_Prospectus']")
        await jc_pill.click()
        await page.wait_for_timeout(1000)

        # 5. Check hero button text
        hero_btn = page.locator("#btnHeroSync")
        btn_text = await page.locator("#btnHeroText").inner_text()
        print(f"[PLAYWRIGHT] Hero button text: {btn_text}")
        assert "SYNC 07 JOHNNY CARROLL TO DRIVE NOW" in btn_text

        # 6. Capture Visual Twin Screenshot
        print(f"[PLAYWRIGHT] Capturing full-page visual twin to {output_image}...")
        await page.screenshot(path=output_image, full_page=True)
        assert os.path.exists(output_image), "Screenshot file was not created"
        size_kb = os.path.getsize(output_image) / 1024
        print(f"[PLAYWRIGHT SUCCESS] Visual Twin captured ({size_kb:.1f} KB): {output_image}")

        await browser.close()
        print("[PLAYWRIGHT SUCCESS] All verification criteria passed flawlessly!")

if __name__ == "__main__":
    asyncio.run(verify_and_capture())
