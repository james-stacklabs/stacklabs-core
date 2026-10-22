import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    print("🚀 Running FanStack verification...")
    errors = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors", "--disable-web-security"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )
        
        # Inject auth localStorage
        await context.add_init_script("""
            localStorage.setItem('sov_auth', 'unlocked');
            localStorage.setItem('auth_token', 'sovereign_admin');
            localStorage.setItem('sovereign_user', 'james');
            localStorage.setItem('sovereign_role', 'admin');
        """)
        
        page = await context.new_page()
        
        # Track console messages
        def log_console(msg):
            if msg.type == "error":
                errors.append(f"Console error: {msg.text}")
                print(f"🔴 Console error: {msg.text}")
            else:
                print(f"💬 Console: {msg.text}")
                
        page.on("console", log_console)
        
        # Track failed requests (especially 404s)
        def log_response(response):
            status = response.status
            url = response.url
            if status >= 400:
                errors.append(f"HTTP {status}: {url}")
                print(f"🔴 HTTP {status}: {url}")
                
        page.on("response", log_response)
        
        # Navigate to FanStack portal (HTTPS 3009)
        # Navigate to FanStack portal (HTTPS 3009)
        url = "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=advocate_center"
        print(f"Navigating to {url}...")
        try:
            await page.goto(url, wait_until="load", timeout=15000)
        except Exception as e:
            print(f"Timeout / error navigating: {e}")

        # Check for login form and fill it
        try:
            username_input = await page.query_selector("#auth-username")
            password_input = await page.query_selector("#auth-password")
            if username_input and password_input:
                print("Lock screen detected. Logging in...")
                await username_input.fill("james")
                await password_input.fill("!!Stella1977")
                await page.click("#auth-submit")
                await page.wait_for_timeout(4000)
        except Exception as e:
            print(f"Error filling login form: {e}")
            
        await page.wait_for_timeout(3000)
        
        # Take screenshot
        os.makedirs("/home/james/stacklabs/uat_screenshots", exist_ok=True)
        screenshot_path = "/home/james/stacklabs/uat_screenshots/fanstack_verification.png"
        await page.screenshot(path=screenshot_path)
        print(f"Captured screenshot at {screenshot_path}")
        
        # Verify if BobbyBonillaHater is visible or mentioned
        body_content = await page.content()
        if "bobbybonillahater" in body_content.lower() or "deferred payment" in body_content.lower() or "siravo" in body_content.lower():
            print("✅ Verified: BobbyBonillaHater (Sal Siravo) found in page content!")
        else:
            print("⚠️ Warning: BobbyBonillaHater not found in rendered text content.")
            
        await browser.close()
        
    print(f"\nVerification summary: {len(errors)} errors found.")
    if errors:
        print("Detailed errors:")
        for err in errors:
            print(f" - {err}")
    else:
        print("✅ No HTTP errors or console errors detected!")

if __name__ == "__main__":
    asyncio.run(run())
