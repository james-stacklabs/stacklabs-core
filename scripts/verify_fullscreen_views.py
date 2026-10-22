import asyncio
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
        await page.goto("https://clio.taila01894.ts.net:3035/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # 1. Ethical Wall Vaults (Drawer closed)
        await page.click("button:has-text('Ethical Wall Vaults')")
        await page.wait_for_timeout(500)
        await page.screenshot(path="/home/james/stacklabs/27_Sovereign_Legal/veritas_vaults_fullscreen.png", full_page=True)

        # 2. Deposition Matrix
        await page.click("button:has-text('Deposition Matrix')")
        await page.wait_for_timeout(500)
        await page.screenshot(path="/home/james/stacklabs/27_Sovereign_Legal/veritas_deposition_matrix_fullscreen.png", full_page=True)

        # 3. OCG Billing Guard
        await page.click("button:has-text('OCG Billing Guard')")
        await page.wait_for_timeout(500)
        await page.screenshot(path="/home/james/stacklabs/27_Sovereign_Legal/veritas_ocg_guard_fullscreen.png", full_page=True)

        print("All fullscreen views captured!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
