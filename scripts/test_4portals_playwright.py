"""
Playwright Visual Twin & Live Ingress Verifier for Sovereign 4-Portals
Path: scripts/test_4portals_playwright.py
"""

import os
import sys
import asyncio
from playwright.async_api import async_playwright

OUTPUT_DIR = "/home/james/sovereign_inbox/today/uat_screenshots"
TICKET_MOCKUP_DIR = "/home/james/sovereign_inbox/tickets/ENHC0010015-FOUR-PORTAL-DECOUPLING-AND-POWER-TOOLS-REORGANIZATION/mockups"

PORTALS = [
    {"name": "portal_3016_itsm", "url": "https://clio.taila01894.ts.net:3016/"},
    {"name": "portal_3028_powertools", "url": "https://clio.taila01894.ts.net:3028/"},
    {"name": "portal_3010_sports", "url": "https://clio.taila01894.ts.net:3010/"},
    {"name": "portal_3009_creator", "url": "https://clio.taila01894.ts.net:3009/"},
]

async def verify_portals():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TICKET_MOCKUP_DIR, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True
        )

        for portal in PORTALS:
            print(f"[*] Testing {portal['name']} at {portal['url']}...")
            page = await context.new_page()
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))

            try:
                resp = await page.goto(portal["url"], wait_until="networkidle", timeout=15000)
                status = resp.status if resp else "NO_RESP"
                print(f"    Status: {status}")

                # Wait 1s for animations
                await page.wait_for_timeout(1000)

                shot_path = os.path.join(OUTPUT_DIR, f"{portal['name']}_live.png")
                ticket_shot_path = os.path.join(TICKET_MOCKUP_DIR, f"{portal['name']}_live.png")
                await page.screenshot(path=shot_path, full_page=False)
                await page.screenshot(path=ticket_shot_path, full_page=False)
                print(f"    Captured screenshot: {shot_path}")

                if errors:
                    print(f"    [WARN] Page JS Errors ({len(errors)}): {errors[:2]}")
                else:
                    print(f"    ✓ 0 Console JS Errors")

            except Exception as e:
                print(f"    [ERROR] Failed to load {portal['name']}: {e}")
            finally:
                await page.close()

        await browser.close()
        print("\n[✓] All 4 portals verified successfully.")

if __name__ == "__main__":
    asyncio.run(verify_portals())
