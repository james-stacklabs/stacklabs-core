#!/usr/bin/env python3
"""
Sovereign OS: Creator Portal Slate & Navigation Refactor Playwright Verification
Path: /home/james/stacklabs/scripts/verify_fanstack_refactor.py
Ticket: WO-2026-0910-CREATOR-PORTAL-SLATE-AND-NAV-REFACTOR
"""

import os
import sys
import time
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "https://clio.taila01894.ts.net:3009"
TICKET_DIR = Path("/home/james/sovereign_inbox/tickets/WO-2026-0910-CREATOR-PORTAL-SLATE-AND-NAV-REFACTOR")
UAT_DIR = TICKET_DIR / "uat"
BRAIN_DIR = Path("/home/james/.gemini/antigravity-ide/brain/d79fcd69-cbad-4b69-89a1-3c8fe9409116")
UAT_DIR.mkdir(parents=True, exist_ok=True)

def verify_refactor():
    print("[*] Starting FanStack Creator Portal Refactor Verification...")
    screenshots = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # SESSION 1: CREATOR VIEW (Tyler Ward @WardyNYM Experience)
        # -------------------------------------------------------------
        context_creator = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        context_creator.add_init_script("""
            localStorage.setItem('sov_auth', 'unlocked');
            localStorage.setItem('sov_role_override', 'creator');
            localStorage.setItem('sovereign_theme', 'sovereign-home');
        """)
        page_creator = context_creator.new_page()

        print("[➔] Loading Creator Portal Home (Clean Experience)...")
        page_creator.goto(f"{BASE_URL}/?domain=PORTAL&role=creator", wait_until="domcontentloaded", timeout=15000)
        page_creator.wait_for_timeout(3000)

        path_creator_home = UAT_DIR / "01_creator_portal_home.png"
        page_creator.screenshot(path=str(path_creator_home), full_page=False)
        screenshots["01_creator_portal_home"] = str(path_creator_home)

        # Test Slate Collapse in Creator View
        print("[➔] Testing Creator Slate Collapse Toggle...")
        collapse_btn = page_creator.locator("button:has-text('COLLAPSE')")
        if collapse_btn.count() > 0:
            collapse_btn.first.click()
            page_creator.wait_for_timeout(1000)
            path_creator_collapsed = UAT_DIR / "02_creator_slate_collapsed.png"
            page_creator.screenshot(path=str(path_creator_collapsed), full_page=False)
            screenshots["02_creator_slate_collapsed"] = str(path_creator_collapsed)

            # Re-expand slate
            expand_bar = page_creator.locator("button:has-text('EXPAND SLATE')")
            if expand_bar.count() > 0:
                expand_bar.first.click()
                page_creator.wait_for_timeout(1000)

        # Command Center in Creator View
        print("[➔] Navigating to Command Center in Creator View...")
        page_creator.goto(f"{BASE_URL}/?domain=MLB&room=starter&role=creator", wait_until="domcontentloaded", timeout=15000)
        page_creator.wait_for_timeout(3000)

        path_creator_cmd = UAT_DIR / "03_creator_command_center.png"
        page_creator.screenshot(path=str(path_creator_cmd), full_page=False)
        screenshots["03_creator_command_center"] = str(path_creator_cmd)

        sidebar_creator = page_creator.locator("aside")
        if sidebar_creator.count() > 0:
            path_creator_sidebar = UAT_DIR / "04_creator_sidebar_15_tools.png"
            sidebar_creator.first.screenshot(path=str(path_creator_sidebar))
            screenshots["04_creator_sidebar_15_tools"] = str(path_creator_sidebar)

        # HoloDex in Creator View
        print("[➔] Verifying HoloDex Global Slate in Creator View...")
        page_creator.goto(f"{BASE_URL}/?domain=GLOBAL&room=holodex&role=creator", wait_until="domcontentloaded", timeout=15000)
        page_creator.wait_for_timeout(3000)
        path_creator_holodex = UAT_DIR / "05_creator_holodex_global_slate.png"
        page_creator.screenshot(path=str(path_creator_holodex), full_page=False)
        screenshots["05_creator_holodex_global_slate"] = str(path_creator_holodex)

        # -------------------------------------------------------------
        # SESSION 2: PILOT VIEW (Lead Architect Experience)
        # -------------------------------------------------------------
        context_pilot = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        context_pilot.add_init_script("""
            localStorage.setItem('sov_auth', 'unlocked');
            localStorage.setItem('sov_role_override', 'pilot');
            localStorage.setItem('sovereign_theme', 'sovereign-home');
        """)
        page_pilot = context_pilot.new_page()

        print("[➔] Loading Pilot Portal Home (Infrastructure Controls Active)...")
        page_pilot.goto(f"{BASE_URL}/?domain=PORTAL&role=pilot", wait_until="domcontentloaded", timeout=15000)
        page_pilot.wait_for_timeout(3000)

        path_pilot_home = UAT_DIR / "06_pilot_portal_home_with_devops.png"
        page_pilot.screenshot(path=str(path_pilot_home), full_page=False)
        screenshots["06_pilot_portal_home_with_devops"] = str(path_pilot_home)

        browser.close()

    # Copy all screenshots to brain directory for artifact embedding
    for name, filepath in screenshots.items():
        dest = BRAIN_DIR / Path(filepath).name
        try:
            shutil.copy2(filepath, dest)
            print(f"[✓] Copied {Path(filepath).name} to brain directory.")
        except Exception as e:
            print(f"[!] Copy error: {e}")

    print("\n[✓] Verification Complete! All screenshots captured:")
    for k, v in screenshots.items():
        print(f" - {k}: {v}")

if __name__ == "__main__":
    verify_refactor()
