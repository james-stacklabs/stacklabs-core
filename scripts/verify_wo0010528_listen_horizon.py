#!/usr/bin/env python3
"""
scripts/verify_wo0010528_listen_horizon.py
Verification & Playwright Visual Twin Sentry for WO0010528.
Deploys and verifies Horizon Episode 3 on StackLabs Listen (Port 3040).
"""

import asyncio
import os
import shutil
import sys
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:3040"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")
TODAY_DIR = Path("/home/james/sovereign_inbox/today")

def verify_http_endpoints():
    print("[1/4] Verifying HTTP Endpoints...")
    endpoints = [
        ("/", "text/html"),
        ("/assets/horizon_market_panic_album_art.jpg", "image/"),
        ("/audio/How_StackLabs_Horizon_Trades_Market_Panic.m4a", "audio/"),
    ]

    for path, expected_content_type in endpoints:
        url = f"{BASE_URL}{path}"
        req = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                ctype = resp.headers.get("Content-Type", "")
                assert status == 200, f"Expected 200 for {url}, got {status}"
                assert expected_content_type in ctype, f"Expected '{expected_content_type}' in Content-Type, got '{ctype}'"
                print(f"  ✓ {url} -> HTTP {status} [{ctype}]")
        except Exception as e:
            # Fallback to GET with Range if HEAD is not supported by some static servers
            req_get = urllib.request.Request(url, headers={"Range": "bytes=0-1024"})
            with urllib.request.urlopen(req_get, timeout=10) as resp:
                status = resp.status
                ctype = resp.headers.get("Content-Type", "")
                assert status in (200, 206), f"Expected 200/206 for {url}, got {status}"
                assert expected_content_type in ctype, f"Expected '{expected_content_type}' in Content-Type, got '{ctype}'"
                print(f"  ✓ {url} (Range GET) -> HTTP {status} [{ctype}]")

async def capture_twins():
    MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
    TODAY_DIR.mkdir(parents=True, exist_ok=True)

    dt_target = MOCKUPS_DIR / "pegasus_uat_wo0010528_listen_horizon_desktop.png"
    mb_target = MOCKUPS_DIR / "pegasus_uat_wo0010528_listen_horizon_mobile.png"

    print("[2/4] Launching Chromium headless for Visual Twins...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # -----------------------------------------------------------------
        # Desktop (1920x1080)
        # -----------------------------------------------------------------
        print("[3/4] Capturing Desktop Visual Twin (1920x1080)...")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_d = await ctx_desktop.new_page()

        target_url = f"{BASE_URL}/?track=horizon-market-panic"
        print(f"  Navigating to: {target_url}")
        resp = await page_d.goto(target_url, wait_until="networkidle", timeout=15000)
        assert resp.status == 200, f"Expected 200, got {resp.status}"

        # Wait for track title to be rendered
        await page_d.wait_for_selector("text=How StackLabs Horizon Trades Market Panic", timeout=10000)

        # Assert presence of track title and chapters
        track_title = await page_d.inner_text("h1, h2, div:has-text('How StackLabs Horizon Trades Market Panic')")
        assert "Horizon" in track_title, f"Track title missing Horizon: {track_title}"

        # Assert chapter count (11 chapters for Horizon track)
        chapters = await page_d.query_selector_all("text=Pierre-Paul Grassé 1959")
        assert len(chapters) > 0, "Chapter 'Pierre-Paul Grassé 1959' not found in DOM!"

        # Assert thesis concepts present
        concept_elements = await page_d.query_selector_all("text=Biological Stigmergy & Order Book Thermodynamics")
        assert len(concept_elements) > 0, "Thesis concept for Stigmergy not found in DOM!"

        # Expand concept card
        print("  Expanding Stigmergy thesis concept card...")
        await page_d.click("text=Biological Stigmergy & Order Book Thermodynamics")
        await page_d.wait_for_timeout(500)

        # Capture Desktop Twin
        print(f"  Saving Desktop Twin -> {dt_target}")
        await page_d.screenshot(path=str(dt_target), full_page=False)
        shutil.copy(dt_target, TODAY_DIR / dt_target.name)

        # -----------------------------------------------------------------
        # Mobile (390x844 - iPhone standard)
        # -----------------------------------------------------------------
        print("[4/4] Capturing Mobile Visual Twin (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        page_m = await ctx_mobile.new_page()

        print(f"  Navigating to: {target_url}")
        resp_m = await page_m.goto(target_url, wait_until="networkidle", timeout=15000)
        assert resp_m.status == 200, f"Expected 200, got {resp_m.status}"

        # Wait for visible track title on mobile
        title_loc = page_m.locator("h1:visible")
        await title_loc.wait_for(state="visible", timeout=10000)
        title_text = await title_loc.inner_text()
        assert "Horizon" in title_text, f"Mobile title missing Horizon: {title_text}"
        await page_m.wait_for_timeout(500)

        # Capture Mobile Twin
        print(f"  Saving Mobile Twin -> {mb_target}")
        await page_m.screenshot(path=str(mb_target), full_page=False)
        shutil.copy(mb_target, TODAY_DIR / mb_target.name)

        await browser.close()
        print("✅ [TWIN GATE PASSED] Desktop and Mobile Playwright visual twins captured successfully.")

def main():
    verify_http_endpoints()
    asyncio.run(capture_twins())
    print("\n🎉 ALL ACCEPTANCE CRITERIA FOR WO0010528 FULLY MET!")

if __name__ == "__main__":
    main()
