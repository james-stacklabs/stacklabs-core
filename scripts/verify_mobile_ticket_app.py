import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    target_dir = "/home/james/sovereign_inbox/tickets/WO-2026-0903-MOBILE-TICKET-APP/mockups"
    brain_dir = "/home/james/.gemini/antigravity-ide/brain/1802fbba-a2f0-4e01-9037-486afd434b5f"
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(brain_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 412, "height": 915},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        print("Navigating to https://clio.taila01894.ts.net:3029/ ...")
        await page.goto("https://clio.taila01894.ts.net:3029/", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        
        feed_path = os.path.join(target_dir, "live_browser_feed.png")
        feed_brain_path = os.path.join(brain_dir, "live_browser_feed.png")
        await page.screenshot(path=feed_path, full_page=False)
        await page.screenshot(path=feed_brain_path, full_page=False)
        print(f"Captured live feed screenshot to {feed_path}")

        # Click on the first ticket card to open bottom sheet
        cards = await page.query_selector_all(".cursor-pointer")
        if cards:
            print(f"Clicking on first ticket card of {len(cards)}...")
            await cards[0].click()
            await page.wait_for_timeout(1000)
            
            sheet_path = os.path.join(target_dir, "live_browser_bottomsheet.png")
            sheet_brain_path = os.path.join(brain_dir, "live_browser_bottomsheet.png")
            await page.screenshot(path=sheet_path, full_page=False)
            await page.screenshot(path=sheet_brain_path, full_page=False)
            print(f"Captured live bottom sheet screenshot to {sheet_path}")

        await browser.close()
        print("Visual verification complete!")

if __name__ == "__main__":
    asyncio.run(run())
