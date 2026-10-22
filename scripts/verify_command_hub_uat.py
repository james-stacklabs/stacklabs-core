import asyncio
from playwright.async_api import async_playwright
import os

async def run_uat():
    print("🚀 Initializing Playwright Headless UAT for Sovereign Command Hub...")
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
        # Set cookies and storage
        await page.add_init_script("""
            sessionStorage.setItem('sov_auth', 'unlocked');
            localStorage.setItem('sovereign_session_token', 'pilot_omega_valid');
            localStorage.setItem('sovereign_user_name', 'james');
            localStorage.setItem('sovereign_role', 'pilot');
        """)
        
        url = "https://clio.taila01894.ts.net:3016/?room=command_hub&vip=creator"
        print(f"📡 Navigating to: {url}")
        
        response = await page.goto(url, wait_until="load", timeout=20000)
        print(f"✅ Response status: {response.status if response else 'Unknown'}")
        
        await asyncio.sleep(3)
        
        # Check what is rendered
        content = await page.content()
        print(f"Page title: {await page.title()}")
        print(f"Page URL: {page.url}")
        
        # Screenshot debug
        os.makedirs("/home/james/sovereign_inbox/today/uat_screenshots", exist_ok=True)
        debug_shot = "/home/james/sovereign_inbox/today/uat_screenshots/debug_page.png"
        await page.screenshot(path=debug_shot, full_page=True)
        print(f"📸 Debug screenshot saved to: {debug_shot}")
        
        # Check if ExtranetGate is visible
        if "Enter Gate Passcode" in content or "EXTRANET" in content:
            print("🔑 ExtranetGate detected. Typing passcode SOV2026...")
            inputs = await page.locator("input").all()
            if inputs:
                await inputs[0].fill("SOV2026")
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
        
        # Wait for Sovereign Command Hub
        print("🔍 Checking for Command Hub elements...")
        await page.wait_for_selector("text=Sovereign Command Hub", timeout=10000)
        print("✅ Found Sovereign Command Hub header!")
        
        # Matrix View Screenshot
        matrix_shot = "/home/james/sovereign_inbox/today/uat_screenshots/live_command_hub_matrix_view.png"
        await page.screenshot(path=matrix_shot, full_page=True)
        print(f"📸 Captured live Matrix View screenshot: {matrix_shot}")
        
        # Switch to Kinetic Physics Lab tab
        print("⚡ Switching to Kinetic Physics Lab tab...")
        lab_tab = page.locator("button:has-text('Kinetic Physics Lab')")
        await lab_tab.click()
        await asyncio.sleep(2)
        
        # Physics Lab View Screenshot
        lab_shot = "/home/james/sovereign_inbox/today/uat_screenshots/live_command_hub_physics_lab_view.png"
        await page.screenshot(path=lab_shot, full_page=True)
        print(f"📸 Captured live Physics Lab View screenshot: {lab_shot}")
        
        # Copy to brain dir
        brain_dir = "/home/james/.gemini/antigravity/brain/e3c45a14-6b29-4c1c-9da0-e0344fd40bc8"
        os.system(f"cp {matrix_shot} {brain_dir}/")
        os.system(f"cp {lab_shot} {brain_dir}/")
        
        await browser.close()
        print("🏁 UAT Verification Run Complete!")

if __name__ == "__main__":
    asyncio.run(run_uat())
