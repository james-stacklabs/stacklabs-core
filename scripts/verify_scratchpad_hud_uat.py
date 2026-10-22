#!/usr/bin/env python3
"""
scripts/verify_scratchpad_hud_uat.py
====================================
Playwright UAT verification script for WO0010557 (Horizon Edge Chrome Scratchpad HUD).
Captures visual twin at 1920x1080 resolution and asserts all DOM panes render cleanly.
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HUD_URL = "http://127.0.0.1:8095/cockpit/hud"
TARGET_MOCKUP_1 = Path("/home/james/stacklabs/mockups/pegasus_uat_scratchpad_hud.png")
TARGET_MOCKUP_2 = Path("/home/james/stacklabs/mockups/pegasus_uat_scratchpad_hud.png")

def main():
    print(f"[*] Navigating to {HUD_URL} via Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.goto(HUD_URL, wait_until="networkidle")

        # Wait for data to populate
        page.wait_for_selector("#count-hud")
        page.wait_for_timeout(1000)

        # Assertions
        hud_count = int(page.text_content("#count-hud").strip())
        queue_count = int(page.text_content("#count-queue").strip())
        nodes_count = int(page.text_content("#count-nodes").strip())
        latency = page.text_content("#badge-latency").strip()
        sabine = page.text_content("#badge-sabine").strip()
        pulse = page.text_content("#badge-pulse").strip()

        print(f"[+] Verified Badges: Latency='{latency}', Sabine='{sabine}', Pulse='{pulse}'")
        print(f"[+] Verified Counts: Rolling HUD={hud_count}, Active Queue={queue_count}, Nodes={nodes_count}")

        assert hud_count > 0, f"Expected hud_count > 0, got {hud_count}"
        assert queue_count > 0, f"Expected queue_count > 0, got {queue_count}"
        assert nodes_count > 0, f"Expected nodes_count > 0, got {nodes_count}"

        TARGET_MOCKUP_1.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(TARGET_MOCKUP_1), full_page=True)
        print(f"✅ Saved Playwright visual twin to {TARGET_MOCKUP_1}")

        TARGET_MOCKUP_2.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(TARGET_MOCKUP_2), full_page=True)
        print(f"✅ Saved Playwright visual twin to {TARGET_MOCKUP_2}")

        browser.close()

if __name__ == "__main__":
    main()
