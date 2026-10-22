import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            ignore_https_errors=True
        )
        page = await context.new_page()
        url = "https://clio.taila01894.ts.net:3016/?view=mobile_deck"
        print(f"Navigating to {url}...")
        
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # 1. Capture Full Default Mobile Deck
        out_main = r"/home/james/sovereign_inbox/uat_screenshots/live_mobile_command_deck.png"
        await page.screenshot(path=out_main, full_page=True)
        print(f"Main screenshot saved to {out_main}")
        
        # 2. Click Boggs Level 4 (Agitator)
        boggs4 = page.locator("button:has-text('Agitator')")
        if await boggs4.count() > 0:
            print("Clicking Boggs Level 4...")
            await boggs4.first.click(force=True)
            await page.wait_for_timeout(1000)
            
        # 3. Click Authorize (Omega=1)
        auth_btn = page.locator("button:has-text('AUTHORIZE')")
        if await auth_btn.count() > 0:
            print("Clicking AUTHORIZE button...")
            await auth_btn.first.click(force=True)
            await page.wait_for_timeout(1500)
            
        out_auth = r"/home/james/sovereign_inbox/uat_screenshots/live_mobile_jit_approvals.png"
        await page.screenshot(path=out_auth, full_page=True)
        print(f"Interaction screenshot saved to {out_auth}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
