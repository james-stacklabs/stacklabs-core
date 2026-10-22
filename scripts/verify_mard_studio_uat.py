import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    output_dir = os.path.expanduser('~/.gemini/antigravity/brain/00d97e4d-a748-4ea5-af76-80aa00048da8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1600, 'height': 1100}, ignore_https_errors=True)
        page = await context.new_page()
        
        print("Navigating to M.A.R.D. NEXUS STUDIO sandbox app over HTTPS on port 3030...")
        await page.goto("https://clio.taila01894.ts.net:3030/", wait_until="networkidle", timeout=15000)

        # Click HOLODEX ENGINE tab
        print("Clicking HOLODEX ENGINE tab...")
        await page.click("text=HOLODEX ENGINE")
        await page.wait_for_timeout(1500)
        shot_holodex = os.path.join(output_dir, 'playwright_mard_holodex_pro_live.png')
        await page.screenshot(path=shot_holodex, full_page=True)
        print(f"Captured HoloDex Studio Pro HTTPS screenshot: {shot_holodex}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
