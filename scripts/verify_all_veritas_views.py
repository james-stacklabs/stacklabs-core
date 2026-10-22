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

        # 1. Open Vincent Drawer and send a test query
        await page.click("button:has-text('Ask Vincent on Clio')")
        await page.wait_for_timeout(500)
        await page.fill("input[placeholder*='Ask Vincent']", "INDEMNIFICATION survival period")
        await page.click("button[type='submit']")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="/home/james/stacklabs/27_Sovereign_Legal/veritas_vincent_drawer.png", full_page=True)
        print("Vincent Drawer screenshot captured!")

        # 2. Switch to Ethical Wall Vault tab
        await page.click("button:has-text('Ethical Wall Vaults')")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="/home/james/stacklabs/27_Sovereign_Legal/veritas_vaults.png", full_page=True)
        print("Ethical Wall Vaults screenshot captured!")

        # 3. Switch to Deposition Matrix tab
        await page.click("button:has-text('Deposition Matrix')")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="/home/james/stacklabs/27_Sovereign_Legal/veritas_deposition_matrix.png", full_page=True)
        print("Deposition Matrix screenshot captured!")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
