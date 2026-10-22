#!/usr/bin/env python3
"""
Playwright Evolution Crawler: WildSeed Extracts 3-Era Transformation
Captures desktop (1920x1080) and mobile (390x844) viewport screenshots across:
  Era 1: https://wildseedextracts.com (Legacy WordPress / Dutchie Menu)
  Era 2: https://www.stacklabsllc.com/wildseed_genesis (15-Word Blind Genesis Prototype)
  Era 3: https://www.stacklabsllc.com/wildseed (Modern Edge Platform)

Saves output to: /home/james/sovereign_inbox/today/uat_screenshots/
"""

import sys
import os
import time
from pathlib import Path

# Ensure execution in sovereign venv if playwright is not in global environment
try:
    import playwright
except ImportError:
    venv_python = "/home/james/stacklabs/.venv/bin/python3"
    if os.path.exists(venv_python) and sys.executable != venv_python:
        os.execv(venv_python, [venv_python] + sys.argv)
    raise

from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("/home/james/sovereign_inbox/today/uat_screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    {
        "era": "Era 1 (Legacy WordPress / Dutchie Menu)",
        "url": "https://wildseedextracts.com",
        "desktop_filename": "wildseed_legacy_wordpress_desktop.png",
        "mobile_filename": "wildseed_legacy_wordpress_mobile.png",
        "is_legacy": True,
    },
    {
        "era": "Era 2 (15-Word Blind Genesis Prototype)",
        "url": "https://www.stacklabsllc.com/wildseed_genesis",
        "desktop_filename": "wildseed_blind_genesis_desktop.png",
        "mobile_filename": "wildseed_blind_genesis_mobile.png",
        "is_legacy": False,
    },
    {
        "era": "Era 3 (Modern Edge Platform)",
        "url": "https://www.stacklabsllc.com/wildseed",
        "desktop_filename": "wildseed_react_edge_desktop.png",
        "mobile_filename": "wildseed_react_edge_mobile.png",
        "is_legacy": False,
    },
]

def clear_legacy_overlays(page):
    """Safely clear age gate and unlock scroll on legacy WordPress site."""
    try:
        page.evaluate("""() => {
            const ageGate = document.querySelector('.sg_age-verification');
            if (ageGate) {
                ageGate.remove();
            }
            const modalBackdrop = document.querySelector('.modal-backdrop');
            if (modalBackdrop) {
                modalBackdrop.remove();
            }
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
        }""")
        print("  [Age Gate] Successfully cleared overlay.")
    except Exception as e:
        print(f"  [Age Gate] Notice: {e}")

def crawl():
    print("🌿 [WildSeed Evolution Crawler] Starting Playwright captures...")
    print(f"📁 Destination directory: {OUTPUT_DIR}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for target in TARGETS:
            era_name = target["era"]
            url = target["url"]
            print(f"━━━ Capturing {era_name} ({url}) ━━━")

            # 1. Desktop Viewport (1920x1080)
            desktop_path = OUTPUT_DIR / target["desktop_filename"]
            print(f"  📸 Desktop (1920x1080) -> {desktop_path.name}")
            desktop_context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                device_scale_factor=1,
            )
            desktop_page = desktop_context.new_page()
            try:
                desktop_page.goto(url, wait_until="domcontentloaded", timeout=30000)
                desktop_page.wait_for_timeout(2000)
                if target.get("is_legacy"):
                    clear_legacy_overlays(desktop_page)
                desktop_page.wait_for_timeout(2000)
                desktop_page.screenshot(path=str(desktop_path), full_page=False)
                size_kb = desktop_path.stat().st_size / 1024
                print(f"  ✔ Desktop captured: {size_kb:.1f} KB")
            except Exception as e:
                print(f"  ❌ Error capturing desktop: {e}")
            finally:
                desktop_context.close()

            # 2. Mobile Viewport iPhone 15 (390x844)
            mobile_path = OUTPUT_DIR / target["mobile_filename"]
            print(f"  📱 Mobile (390x844) -> {mobile_path.name}")
            mobile_context = browser.new_context(
                viewport={"width": 390, "height": 844},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
                is_mobile=True,
                has_touch=True,
                device_scale_factor=2,
            )
            mobile_page = mobile_context.new_page()
            try:
                mobile_page.goto(url, wait_until="domcontentloaded", timeout=30000)
                mobile_page.wait_for_timeout(2000)
                if target.get("is_legacy"):
                    clear_legacy_overlays(mobile_page)
                mobile_page.wait_for_timeout(2000)
                mobile_page.screenshot(path=str(mobile_path), full_page=False)
                size_kb = mobile_path.stat().st_size / 1024
                print(f"  ✔ Mobile captured: {size_kb:.1f} KB")
            except Exception as e:
                print(f"  ❌ Error capturing mobile: {e}")
            finally:
                mobile_context.close()

            print()

        browser.close()

    print("🏁 [WildSeed Evolution Crawler] Verification check of emitted assets:")
    all_success = True
    for target in TARGETS:
        for fname in [target["desktop_filename"], target["mobile_filename"]]:
            fpath = OUTPUT_DIR / fname
            if fpath.exists() and fpath.stat().st_size > 1000:
                print(f"  ✅ {fname} ({fpath.stat().st_size / 1024:.1f} KB)")
            else:
                print(f"  ❌ Missing or empty: {fname}")
                all_success = False

    if all_success:
        print("\n✨ All 6 visual twin assets captured successfully!")
    else:
        print("\n⚠️ Warning: One or more screenshot captures failed.")
        sys.exit(1)

if __name__ == "__main__":
    crawl()
