import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True
        )
        page = await context.new_page()

        url = "https://127.0.0.1:3031/"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        # Wait for the canvas and HUD to mount
        await page.wait_for_selector("canvas", timeout=10000)
        await page.wait_for_selector("text=BALLPARKRADAR", timeout=10000)
        print("Canvas and Radar HUD mounted!")

        # Allow canvas animation to render ball arc and mesh
        await page.wait_for_timeout(2500)

        out_path = "/home/james/.gemini/antigravity-ide/brain/4e36d448-3c57-4840-b6f0-587d9ccbaf5a/ballparkradar_live_capture.png"
        await page.screenshot(path=out_path, full_page=True)
        print(f"Screenshot saved to {out_path}")

        # Also copy to ticket mockups directory
        ticket_mockup_path = "/home/james/sovereign_inbox/tickets/IDEA0010004-BALLPARKRADAR-SPATIAL-STATCAST/mockups/live_playwright_capture.png"
        import shutil
        shutil.copy(out_path, ticket_mockup_path)
        print(f"Copied to ticket package: {ticket_mockup_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
