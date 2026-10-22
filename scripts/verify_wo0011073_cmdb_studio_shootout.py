#!/usr/bin/env python3
"""
StackLabs WO0011073 Visual Twin & Functional Verification Script
Path: /home/james/stacklabs/scripts/verify_wo0011073_cmdb_studio_shootout.py
Author: James Carroll (Pilot), Lead Systems Architect
Host: Clio Bare Metal (Beelink SER Mini PC, AMD Ryzen 7 7735HS)
"""

import os
import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:3025/#shootout"
EVIDENCE_DIR = Path("/home/james/stacklabs/evidence/visual_twins")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP_SCREENSHOT = EVIDENCE_DIR / "WO0011073_cmdb_shootout_desktop.png"
MOBILE_SCREENSHOT = EVIDENCE_DIR / "WO0011073_cmdb_shootout_mobile.png"


async def run_verification():
    print(f"[VERIFY PLAYWRIGHT] Launching browser against {BASE_URL}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # -------------------------------------------------------------
        # 1. Desktop Viewport (1920x1080)
        # -------------------------------------------------------------
        print("\n--- 1. Desktop Viewport (1920x1080) ---")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_d = await ctx_desktop.new_page()

        resp = await page_d.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        print(f"Page loaded: HTTP {resp.status if resp else 'N/A'}")

        # Wait for Launch Live Shootout button
        launch_btn = await page_d.wait_for_selector("text=Launch Live Shootout", timeout=8000)
        assert launch_btn, "Launch Live Shootout button not found!"
        print("Clicking 'Launch Live Shootout' button...")
        await launch_btn.click()

        # Wait for Shootout run to complete (PARITY VERIFIED or View Incident in ServiceNow PDI)
        print("Waiting for live shootout completion from ServiceNow PDI WAN & Clio metal...")
        sn_link = await page_d.wait_for_selector("text=View Incident in ServiceNow PDI ↗", timeout=20000)
        assert sn_link, "View Incident in ServiceNow PDI ↗ button not found after shootout run!"
        print("✔ Found button: 'View Incident in ServiceNow PDI ↗'")

        # Verify href
        href = await sn_link.get_attribute("href")
        print(f"✔ ServiceNow Deep Link Href: {href}")
        assert href and "dev186522.service-now.com" in href, f"Invalid ServiceNow URL: {href}"

        # Find and click toggle button: 'Inspect Database Mutations (SQLite vs REST)'
        inspect_btn = await page_d.wait_for_selector("text=Inspect Database Mutations (SQLite vs REST)", timeout=5000)
        assert inspect_btn, "Inspect Database Mutations button not found!"
        print("Clicking 'Inspect Database Mutations (SQLite vs REST)' toggle...")
        await inspect_btn.click()
        await asyncio.sleep(0.5)

        # Verify dual-plane headers and status badge
        header_left = await page_d.wait_for_selector("text=Local State Plane Mutation (vfs/cmdb.db • 0.38ms)", timeout=5000)
        assert header_left, "Header Left not found in drawer!"
        print("✔ Found header: 'Local State Plane Mutation (vfs/cmdb.db • 0.38ms)'")

        header_right = await page_d.wait_for_selector("text=Upstream Cloud Mutation (ServiceNow REST • WAN)", timeout=5000)
        assert header_right, "Header Right not found in drawer!"
        print("✔ Found header: 'Upstream Cloud Mutation (ServiceNow REST • WAN)'")

        badge = await page_d.wait_for_selector("text=MUTATIONS_VERIFIED", timeout=5000)
        assert badge, "Status badge MUTATIONS_VERIFIED not found!"
        print("✔ Found badge: 'MUTATIONS_VERIFIED'")

        # Capture Desktop Screenshot
        await page_d.screenshot(path=str(DESKTOP_SCREENSHOT), full_page=True)
        print(f"✔ Desktop screenshot saved: {DESKTOP_SCREENSHOT} ({DESKTOP_SCREENSHOT.stat().st_size} bytes)")
        await ctx_desktop.close()

        # -------------------------------------------------------------
        # 2. Mobile Viewport (390x844 - iPhone Retina)
        # -------------------------------------------------------------
        print("\n--- 2. Mobile Viewport (390x844) ---")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        page_m = await ctx_mobile.new_page()

        await page_m.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        launch_btn_m = await page_m.wait_for_selector("text=Launch Live Shootout", timeout=8000)
        assert launch_btn_m, "Mobile: Launch Live Shootout button not found!"
        print("Clicking 'Launch Live Shootout' button on mobile...")
        await launch_btn_m.click()

        print("Waiting for mobile shootout completion...")
        sn_link_m = await page_m.wait_for_selector("text=View Incident in ServiceNow PDI ↗", timeout=20000)
        assert sn_link_m, "Mobile: View Incident in ServiceNow PDI ↗ button not found!"
        print("✔ Mobile: Found button 'View Incident in ServiceNow PDI ↗'")

        inspect_btn_m = await page_m.wait_for_selector("text=Inspect Database Mutations (SQLite vs REST)", timeout=5000)
        assert inspect_btn_m, "Mobile: Inspect Database Mutations button not found!"
        await inspect_btn_m.scroll_into_view_if_needed()
        await inspect_btn_m.click(force=True)
        await asyncio.sleep(1.0)

        # Capture Mobile Screenshot
        await page_m.screenshot(path=str(MOBILE_SCREENSHOT), full_page=True)
        print(f"✔ Mobile screenshot saved: {MOBILE_SCREENSHOT} ({MOBILE_SCREENSHOT.stat().st_size} bytes)")
        await ctx_mobile.close()

        await browser.close()
        print("\n[VERIFICATION COMPLETE] All visual twins & assertions validated successfully.")


if __name__ == "__main__":
    asyncio.run(run_verification())
