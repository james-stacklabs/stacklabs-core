import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors", "--disable-gpu", "--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True
        )
        page = await context.new_page()
        print("Navigating to https://clio.taila01894.ts.net:3035/ ...")
        await page.goto("https://clio.taila01894.ts.net:3035/", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        out_path = "/home/james/stacklabs/27_Sovereign_Legal/veritas_live_screenshot.png"
        await page.screenshot(path=out_path, full_page=True)
        print(f"Screenshot successfully captured to {out_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
