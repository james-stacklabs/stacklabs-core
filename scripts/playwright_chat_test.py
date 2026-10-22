import asyncio
import os
import time
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # Launch browser in headful/headless mode
        browser = await p.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors"]
        )
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        # Listen to console events
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        url = "https://clio.taila01894.ts.net:3010/fan-portal?_game_room=824900"
        print(f"Navigating to {url}...")
        await page.goto(url)

        # Wait for the page to load and establish connections
        print("Page loaded. Waiting 15 seconds to capture real-time updates...")
        
        # Take an initial screenshot
        artifact_path_1 = "/home/james/.gemini/antigravity/brain/f4fd333c-3d6b-4322-8502-b5ca2880a48d/playwright_chat_initial.png"
        await page.screenshot(path=artifact_path_1)
        print(f"Saved initial screenshot to {artifact_path_1}")

        # Sleep/wait and let telemetry/chat run
        await asyncio.sleep(15)

        # Take a final screenshot
        artifact_path_2 = "/home/james/.gemini/antigravity/brain/f4fd333c-3d6b-4322-8502-b5ca2880a48d/playwright_chat_final.png"
        await page.screenshot(path=artifact_path_2)
        print(f"Saved final screenshot to {artifact_path_2}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
