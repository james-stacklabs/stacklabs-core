#!/usr/bin/env python3
"""
scripts/verify_wo0010526_briefing_twins.py
Playwright Visual Twin Capture & Verification for WO0010526 (Executive Audio Briefing Portal).
Captures Desktop (1920x1080) and Mobile iPhone (390x844) visual twins.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8088"
AUTH_QUERY = "?key=stacklabs2026"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")
TODAY_DIR = Path("/home/james/sovereign_inbox/today")

async def capture_twins():
    MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
    TODAY_DIR.mkdir(parents=True, exist_ok=True)

    dt_brief = MOCKUPS_DIR / "pegasus_uat_wo0010526_desktop.png"
    mb_brief = MOCKUPS_DIR / "pegasus_uat_wo0010526_mobile.png"
    modal_brief = MOCKUPS_DIR / "pegasus_uat_wo0010526_modal_desktop.png"

    print("[PLAYWRIGHT] Launching Chromium headless on Clio metal...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # -------------------------------------------------------------
        # 1. DESKTOP VIEWPORT (1920x1080)
        # -------------------------------------------------------------
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_d = await ctx_desktop.new_page()

        portal_url = f"{BASE_URL}/{AUTH_QUERY}"
        print(f"[PLAYWRIGHT] Navigating Desktop to Drop Portal: {portal_url}")
        resp = await page_d.goto(portal_url, wait_until="networkidle", timeout=15000)
        assert resp.status == 200, f"Expected 200, got {resp.status}"

        # Ensure Dark Mode
        await page_d.evaluate("setTheme('dark')")
        await page_d.wait_for_timeout(300)

        # Assert DOM presence of tabBtnListen
        assert await page_d.query_selector("#tabBtnListen"), "Missing #tabBtnListen element!"

        # Click Tab: Daily Brief
        print("[PLAYWRIGHT] Clicking #tabBtnListen...")
        await page_d.click("#tabBtnListen")
        await page_d.wait_for_timeout(600)

        # Assert pane visibility
        is_listen_visible = await page_d.evaluate("!document.getElementById('listenPane').classList.contains('hidden')")
        is_drop_hidden = await page_d.evaluate("document.getElementById('dropPane').classList.contains('hidden')")
        is_scrubber_hidden = await page_d.evaluate("document.getElementById('scrubberPane').classList.contains('hidden')")
        assert is_listen_visible, "listenPane must be visible!"
        assert is_drop_hidden, "dropPane must be hidden!"
        assert is_scrubber_hidden, "scrubberPane must be hidden!"

        # Assert episode title and bullet count
        ep_title = await page_d.inner_text("#epTitle")
        assert "The Matrix of Market Panic" in ep_title, f"Unexpected episode title: {ep_title}"
        bullets = await page_d.query_selector_all("#briefBullets li")
        assert len(bullets) >= 3, f"Expected at least 3 bullets, found {len(bullets)}"
        print(f"[PLAYWRIGHT] Verified Desktop Briefing Title: '{ep_title}' with {len(bullets)} bullets")

        # Capture Desktop Twin
        print(f"[PLAYWRIGHT] Capturing Desktop Briefing Twin -> {dt_brief}")
        await page_d.screenshot(path=str(dt_brief), full_page=False)
        shutil.copy(dt_brief, TODAY_DIR / dt_brief.name)

        # Test CarPlay modal
        print("[PLAYWRIGHT] Testing CarPlay subscription modal...")
        await page_d.click("button:has-text('Add to Apple Podcasts')")
        await page_d.wait_for_timeout(300)
        is_modal_visible = await page_d.evaluate("!document.getElementById('podcastModal').classList.contains('hidden')")
        assert is_modal_visible, "podcastModal should be visible!"
        feed_val = await page_d.input_value("#feedUrlInput")
        assert "/api/briefing/feed.xml" in feed_val, f"Unexpected feed URL: {feed_val}"
        print(f"[PLAYWRIGHT] Verified Modal Feed URL: {feed_val}")
        await page_d.screenshot(path=str(modal_brief), full_page=False)

        # Close modal
        await page_d.click("#podcastModal button:has-text('Close')")
        await page_d.wait_for_timeout(200)

        # Test Speed Toggle
        await page_d.click("#speed12")
        await page_d.wait_for_timeout(100)
        playback_rate = await page_d.evaluate("document.getElementById('briefAudioPlayer').playbackRate")
        assert playback_rate == 1.25, f"Expected playbackRate 1.25, got {playback_rate}"
        print("[PLAYWRIGHT] Verified Speed Toggle to 1.25x")

        # -------------------------------------------------------------
        # 2. MOBILE VIEWPORT (390x844 - iPhone 14 / modern standard)
        # -------------------------------------------------------------
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        page_m = await ctx_mobile.new_page()

        print(f"[PLAYWRIGHT] Navigating Mobile to Drop Portal: {portal_url}")
        resp_m = await page_m.goto(portal_url, wait_until="networkidle", timeout=15000)
        assert resp_m.status == 200, f"Expected 200, got {resp_m.status}"

        await page_m.evaluate("setTheme('dark')")
        await page_m.wait_for_timeout(300)

        print("[PLAYWRIGHT] Clicking #tabBtnListen on Mobile...")
        await page_m.click("#tabBtnListen")
        await page_m.wait_for_timeout(600)

        is_m_listen_visible = await page_m.evaluate("!document.getElementById('listenPane').classList.contains('hidden')")
        assert is_m_listen_visible, "listenPane must be visible on mobile!"

        print(f"[PLAYWRIGHT] Capturing Mobile Briefing Twin -> {mb_brief}")
        await page_m.screenshot(path=str(mb_brief), full_page=False)
        shutil.copy(mb_brief, TODAY_DIR / mb_brief.name)

        await browser.close()
        print("✅ [PLAYWRIGHT TWIN GATE] Desktop & Mobile twins captured and verified successfully.")

if __name__ == "__main__":
    asyncio.run(capture_twins())
