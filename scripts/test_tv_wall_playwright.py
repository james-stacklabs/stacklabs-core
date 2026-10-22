import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--ignore-certificate-errors", "--no-sandbox"])
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        # Test 1: Load main fan portal
        url = "https://clio.taila01894.ts.net:3010/fan-portal"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        
        target_path = "/home/james/sovereign_inbox/tickets/DFCT0010003-FANSTACK-TV-WALL-DYNAMIC-TELEMETRY/mockups/live_fan_portal_remediated.png"
        brain_path = "/home/james/.gemini/antigravity-ide/brain/f5e7b9b2-2653-4cb6-a997-cb534a416e88/live_fan_portal_remediated.png"
        uat_path = "/home/james/sovereign_inbox/today/uat_screenshots/live_fan_portal_remediated.png"
        
        await page.screenshot(path=target_path, full_page=False)
        shutil.copy(target_path, brain_path)
        shutil.copy(target_path, uat_path)
        print(f"Captured screenshot to {target_path}")

        # Test 2: Select the rain delayed game (824424)
        url_delay = "https://clio.taila01894.ts.net:3010/fan-portal?_game_room=824424"
        print(f"Navigating to rain delayed game: {url_delay}...")
        await page.goto(url_delay, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        
        delay_path = "/home/james/sovereign_inbox/tickets/DFCT0010003-FANSTACK-TV-WALL-DYNAMIC-TELEMETRY/mockups/live_rain_delayed_game.png"
        delay_brain = "/home/james/.gemini/antigravity-ide/brain/f5e7b9b2-2653-4cb6-a997-cb534a416e88/live_rain_delayed_game.png"
        
        await page.screenshot(path=delay_path, full_page=False)
        shutil.copy(delay_path, delay_brain)
        print(f"Captured screenshot to {delay_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
