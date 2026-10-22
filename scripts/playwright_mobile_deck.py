import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # Launch browser with ignore_https_errors
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        
        # Emulate Pixel viewport
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            ignore_https_errors=True
        )
        
        page = await context.new_page()
        
        # Navigate to Sovereign Portal Mobile Deck
        url = "https://clio.taila01894.ts.net:3016/?view=mobile_deck"
        print(f"Navigating to {url}...")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"Navigation warning: {e}")
            
        await page.wait_for_timeout(3000)
        
        # Ensure output directories exist
        out1 = r"/home/james/sovereign_inbox/uat_screenshots/live_mobile_command_deck.png"
        out2 = r"/home/james/stacklabs/media_vault/live_mobile_command_deck.png"
        os.makedirs(os.path.dirname(out1), exist_ok=True)
        os.makedirs(os.path.dirname(out2), exist_ok=True)
        
        await page.screenshot(path=out1, full_page=True)
        await page.screenshot(path=out2, full_page=True)
        print(f"Screenshot saved to {out1}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
