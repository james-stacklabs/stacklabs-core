#!/usr/bin/env python3
"""
Playwright Visual UAT Capture for WO-2026-0910-FANSTACK-BARF-LOOKBOOK-SEEDER.
Captures live UI screenshots of Barf's 22-Shot Lookbook Modal and dynamic sprite rendering.
"""
import asyncio
import os
from playwright.async_api import async_playwright

UAT_DIR = "/home/james/sovereign_inbox/tickets/WO-2026-0910-FANSTACK-BARF-LOOKBOOK-SEEDER/uat"
os.makedirs(UAT_DIR, exist_ok=True)

async def capture_uat():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--ignore-certificate-errors",
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()

        print("Navigating to Sovereign Sports Dashboard (Port 3010) on /fan-portal?gamePk=822929...")
        try:
            await page.goto("https://localhost:3010/fan-portal?gamePk=822929", timeout=30000, wait_until="networkidle")
        except Exception as e:
            print(f"Navigation fallback: {e}")
            await page.goto("https://localhost:3010/fan-portal?gamePk=822929", timeout=30000, wait_until="domcontentloaded")

        await page.wait_for_timeout(4000)

        # 1. Expand the advocate roster drawer if present
        roster_btn = await page.query_selector("#advocate-roster-toggle-btn")
        if roster_btn:
            print("Clicking advocate roster toggle button...")
            await roster_btn.click()
            await page.wait_for_timeout(1500)

        # Capture Dashboard showing Barf in roster with 22 Poses button
        dash_capture_path = os.path.join(UAT_DIR, "lookbook_active_sprite.png")
        await page.screenshot(path=dash_capture_path, full_page=False)
        print(f"✅ Captured dashboard roster: {dash_capture_path}")

        # 2. Click the '22 Poses' Lookbook button to open the modal
        lookbook_btn = await page.query_selector("button:has-text('22 Poses')")
        if lookbook_btn:
            print("Clicking '22 Poses' Lookbook button...")
            await lookbook_btn.click()
            await page.wait_for_timeout(2500)

            # Capture Lookbook Modal Grid
            modal_capture_path = os.path.join(UAT_DIR, "lookbook_modal_grid.png")
            await page.screenshot(path=modal_capture_path, full_page=False)
            print(f"✅ Captured lookbook modal grid: {modal_capture_path}")

            # Trigger a quick simulation button
            hr_btn = await page.query_selector("button:has-text('Home Run')")
            if hr_btn:
                print("Clicking 'Home Run' sim trigger...")
                await hr_btn.click()
                await page.wait_for_timeout(1500)
                sim_capture_path = os.path.join(UAT_DIR, "lookbook_modal_sim_triggered.png")
                await page.screenshot(path=sim_capture_path, full_page=False)
                print(f"✅ Captured lookbook sim triggered: {sim_capture_path}")
        else:
            print("⚠️ '22 Poses' button not found directly, capturing general state...")

        # 3. Navigate to FanStack Advocate Center (Port 3009)
        print("Navigating to FanStack Advocate Center (Port 3009)...")
        try:
            await page.goto("https://clio.taila01894.ts.net:3009/?room=advocate_center", timeout=30000, wait_until="networkidle")
        except Exception:
            await page.goto("https://localhost:3009/?room=advocate_center", timeout=30000, wait_until="networkidle")

        await page.wait_for_timeout(3000)

        # Find Barf in the advocate list and click to edit
        barf_row = await page.query_selector("div:has-text('barf'), tr:has-text('barf')")
        if barf_row:
            print("Clicking Barf row in Advocate Center...")
            await barf_row.click()
            await page.wait_for_timeout(2000)

        adv_center_capture_path = os.path.join(UAT_DIR, "advocate_center_lookbook.png")
        await page.screenshot(path=adv_center_capture_path, full_page=False)
        print(f"✅ Captured Advocate Center lookbook: {adv_center_capture_path}")

        await browser.close()
        print("🎉 Playwright Visual UAT completed successfully!")

if __name__ == "__main__":
    asyncio.run(capture_uat())
