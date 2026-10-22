import asyncio
from playwright.async_api import async_playwright
import os

async def run_uat():
    print("🚀 Initializing Playwright Headless UAT for Avant-Garde Multi-Model Command Matrix...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--ignore-certificate-errors",
                "--allow-insecure-localhost"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1600, "height": 900},
            ignore_https_errors=True
        )
        
        page = await context.new_page()
        await page.add_init_script("""
            sessionStorage.setItem('sov_auth', 'unlocked');
            localStorage.setItem('sovereign_session_token', 'pilot_omega_valid');
            localStorage.setItem('sovereign_user_name', 'james');
            localStorage.setItem('sovereign_role', 'pilot');
        """)
        
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        url = "https://clio.taila01894.ts.net:3016/?room=command_hub&vip=creator"
        print(f"📡 Navigating to: {url}")
        
        await page.goto(url, wait_until="networkidle", timeout=20000)
        await page.wait_for_selector("text=Sovereign Command Matrix", timeout=10000)
        await asyncio.sleep(2)
        
        # Test Fan-Out: Fill input and click send
        print("⚡ Filling prompt...")
        input_elem = page.locator("input[placeholder*='Type directive']")
        await input_elem.fill("Compare distributed event bus architectures for Sovereign OS")
        await asyncio.sleep(1)
        
        print("⚡ Clicking Send button...")
        send_btn = page.locator("button:has-text('Send')")
        await send_btn.click()
        
        # Wait 3 seconds
        await asyncio.sleep(3)
        
        # Capture Arena screenshot
        arena_shot = "/home/james/sovereign_inbox/today/uat_screenshots/live_avant_garde_matrix_arena.png"
        await page.screenshot(path=arena_shot, full_page=True)
        print(f"📸 Captured live Parallel Dialectic Arena screenshot: {arena_shot}")
        
        # Copy to brain dir
        brain_dir = "/home/james/.gemini/antigravity/brain/e3c45a14-6b29-4c1c-9da0-e0344fd40bc8"
        os.system(f"cp {arena_shot} {brain_dir}/")
        
        print("🔍 Console Logs:")
        for log in console_logs[-15:]:
            print(f"  {log}")
            
        await browser.close()
        print("🏁 UAT Verification Run Complete!")

if __name__ == "__main__":
    asyncio.run(run_uat())
