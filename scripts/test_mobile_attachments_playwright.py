import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            ignore_https_errors=True,
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()

        url = "https://127.0.0.1:3029/?ticket=ENHC0010011-MOBILE-PORTAL-ATTACHMENT-INGRESS"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        # Wait for bottom sheet drawer to open
        await page.wait_for_selector("text=Attachments", timeout=10000)
        print("Attachments section rendered!")

        # Wait a moment for any thumbnail image to load
        await page.wait_for_timeout(2000)

        out_path = "/home/james/sovereign_inbox/tickets/ENHC0010011-MOBILE-PORTAL-ATTACHMENT-INGRESS/mockups/live_playwright_capture.png"
        await page.screenshot(path=out_path, full_page=True)
        print(f"Screenshot saved to {out_path}")

        # Check user-select style
        drawer_user_select = await page.eval_on_selector(
            "h2", "el => window.getComputedStyle(el).userSelect"
        )
        print(f"Title user-select style: {drawer_user_select}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
