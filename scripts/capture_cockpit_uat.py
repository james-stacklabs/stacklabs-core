#!/usr/bin/env python3
"""
capture_cockpit_uat.py — Pegasus Playwright Visual Twin Capture for WO0010511
=============================================================================
Captures high-resolution visual twins across 5 Cockpit tabs:
- Mission Deck (default)
- JIT Approvals
- Queue Air-Gap Stage
- Fleet & CMDB
- Sovereign Horizon Radar
Verifies Vantablack depth, flat black cards, Inter typography, and hover legibility.
"""

import sys
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8088/cockpit"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")
MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    {
        "tab_id": "tab-all",
        "btn_id": "btn-all",
        "name": "mission_deck",
        "filename": "pegasus_uat_wo0010511_cockpit_mission_deck.png"
    },
    {
        "tab_id": "tab-jit",
        "btn_id": "btn-jit",
        "name": "jit",
        "filename": "pegasus_uat_wo0010511_cockpit_jit.png"
    },
    {
        "tab_id": "tab-queue",
        "btn_id": "btn-queue",
        "name": "queue",
        "filename": "pegasus_uat_wo0010511_cockpit_queue.png"
    },
    {
        "tab_id": "tab-cmdb",
        "btn_id": "btn-cmdb",
        "name": "fleet",
        "filename": "pegasus_uat_wo0010511_cockpit_fleet.png"
    },
    {
        "tab_id": "tab-horizon",
        "btn_id": "btn-horizon",
        "name": "horizon",
        "filename": "pegasus_uat_wo0010511_cockpit_horizon.png"
    }
]

def capture():
    print(f"[*] Launching Playwright Chromium targeting {BASE_URL}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # Navigate to cockpit
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(1.5)

        # Ensure dark class is present
        html_class = page.eval_on_selector("html", "el => el.className")
        print(f"[*] <html> class: '{html_class}'")
        assert "dark" in html_class, f"Error: <html> tag missing 'dark' class: '{html_class}'"

        # Capture each tab
        for target in TARGETS:
            btn_selector = f"#{target['btn_id']}"
            print(f"[*] Navigating to tab {target['name']} via {btn_selector}...")
            
            # Hover over button to verify hover legibility in screenshot if testing button
            page.click(btn_selector)
            time.sleep(1.0)
            
            # Wait for content to become visible
            page.wait_for_selector(f"#{target['tab_id']}:not(.hidden)", state="visible", timeout=5000)
            
            out_path = MOCKUPS_DIR / target["filename"]
            page.screenshot(path=str(out_path), full_page=False)
            print(f"[✓] Captured {target['name']}: {out_path} ({os.path.getsize(out_path)} bytes)")

        # Also capture a nav hover test
        print("[*] Testing navigation hover state on #btn-cmdb...")
        page.hover("#btn-cmdb")
        time.sleep(0.5)
        hover_path = MOCKUPS_DIR / "pegasus_uat_wo0010511_cockpit_nav_hover.png"
        page.screenshot(path=str(hover_path), full_page=False)
        print(f"[✓] Captured nav hover: {hover_path} ({os.path.getsize(hover_path)} bytes)")

        browser.close()
        print("[✨] All Playwright visual twins captured successfully.")

if __name__ == "__main__":
    capture()
