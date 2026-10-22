import asyncio
import sys
from playwright.async_api import async_playwright

async def run():
    print("🚀 Initiating Advocate Response Flow Verification Test via Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        url = "https://clio.taila01894.ts.net:3010/fan-portal?game_room=2026082201"
        print(f"🌐 Navigating to {url}...")
        response = await page.goto(url, wait_until="domcontentloaded")
        print(f"HTTP Response Code: {response.status if response else 'None'}")

        await page.wait_for_timeout(4000)

        # Locate chat input
        chat_input = page.locator("input[placeholder*='Inject commentary'], input[placeholder*='commentary']")
        count = await chat_input.count()
        print(f"Chat inputs found: {count}")

        if count > 0:
            msg_text = "Hey Puke and Barf! Giant defense looking solid or is MetLife turf gonna claim Tua?"
            print(f"Typing human commentary: '{msg_text}'...")
            await chat_input.first.fill(msg_text)
            await page.wait_for_timeout(500)
            await chat_input.first.press("Enter")
            print("Message sent! Waiting 9 seconds for advocates to fire back...")
            await page.wait_for_timeout(9000)

        # Take screenshot of live chat box
        screenshot_path = "/home/james/.gemini/antigravity/brain/1e1e745f-ed19-4c4f-90b4-eb66efbee36f/advocate_reply_verification.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 Screenshot saved to {screenshot_path}")

        # Dump visible text in chat panel
        chat_messages = await page.locator("div[class*='chat']").all_text_contents()
        print("\n--- VISIBLE CHAT MESSAGES IN DOM ---")
        for idx, text in enumerate(chat_messages):
            print(f"[{idx}] {text[:200]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
