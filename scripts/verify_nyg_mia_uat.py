import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def run_uat():
    print("🚀 Initializing Full Vertex Playwright UAT for NYG vs MIA NFL Game Room (2026082201)...")
    
    screenshot_path = "/home/james/.gemini/antigravity/brain/1e1e745f-ed19-4c4f-90b4-eb66efbee36f/nyg_mia_playwright_uat.png"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1600, "height": 1000},
            device_scale_factor=1,
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        # Navigate to the FanStack portal room via HTTPS MagicDNS / Localhost
        url = "https://clio.taila01894.ts.net:3010/fan-portal?game_room=2026082201"
        print(f"🌐 Navigating to {url}...")
        
        try:
            response = await page.goto(url, wait_until="networkidle", timeout=15000)
            print(f"HTTP Response Code: {response.status if response else 'OK'}")
        except Exception as e:
            print(f"Networkidle wait timed out, proceeding: {e}")
            await page.goto("https://localhost:3010/fan-portal?game_room=2026082201", wait_until="domcontentloaded")
            
        await page.wait_for_timeout(4000)
        
        # Take full page screenshot
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 Full Vertex UAT Screenshot saved to: {screenshot_path}")
        
        # Validate DOM elements
        content = await page.content()
        
        has_mia = "MIA" in content or "Dolphins" in content
        has_nyg = "NYG" in content or "Giants" in content
        has_zone2 = "[ZONE-2] NFL LIVE SCOREBAR" in content
        has_puke = "puke" in content.lower() or "barf" in content.lower()
        
        print("\n=== UAT VALIDATION REPORT ===")
        print(f"✅ MIA Team Telemetry Detected: {has_mia}")
        print(f"✅ NYG Team Telemetry Detected: {has_nyg}")
        print(f"✅ Zone-2 NFL Scorebar Title Verified: {has_zone2}")
        print(f"✅ Puke / Barf Chatbot Presence Verified: {has_puke}")
        
        await browser.close()
        print("🎉 Full Vertex Playwright UAT Execution Complete!")

if __name__ == "__main__":
    asyncio.run(run_uat())
