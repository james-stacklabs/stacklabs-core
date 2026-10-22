import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    print("🚀 Running Roll Call & Crosstalk Lounge verification...")
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
        
        # Track failed requests
        def log_response(response):
            status = response.status
            url = response.url
            if status >= 400:
                errors.append(f"HTTP {status}: {url}")
                print(f"🔴 HTTP {status}: {url}")
                
        page.on("response", log_response)
        
        # 1. Verify Daily Roll Call
        url1 = "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=roll_call"
        print(f"\nNavigating to Roll Call: {url1}...")
        try:
            await page.goto(url1, wait_until="networkidle", timeout=15000)
        except Exception as e:
            print(f"Timeout / error navigating: {e}")
            
        # Log in if needed
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
            print(f"Error logging in: {e}")
            
        await page.wait_for_timeout(3000)
        
        # Capture Roll Call screenshot
        os.makedirs("/home/james/stacklabs/uat_screenshots", exist_ok=True)
        rc_path = "/home/james/stacklabs/uat_screenshots/daily_roll_call.png"
        await page.screenshot(path=rc_path)
        print(f"Captured Roll Call screenshot at {rc_path}")
        
        # 2. Verify Crosstalk Lounge
        url2 = "https://clio.taila01894.ts.net:3010/fan-portal?gamePk=823607"
        print(f"\nNavigating to Crosstalk Lounge: {url2}...")
        try:
            await page.goto(url2, wait_until="networkidle", timeout=15000)
        except Exception as e:
            print(f"Timeout / error navigating: {e}")
            
        # Log in if needed
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
            print(f"Error logging in: {e}")
            
        await page.wait_for_timeout(5000)
        
        # Capture Crosstalk Lounge screenshot
        cl_path = "/home/james/stacklabs/uat_screenshots/crosstalk_lounge.png"
        await page.screenshot(path=cl_path)
        print(f"Captured Crosstalk Lounge screenshot at {cl_path}")
        
        # Check advocates in rendered page content
        body_content = await page.content()
        advocates = [
            "JoCo_Traitor", "Powder_Blue_85", "salvy_splash_survivor", 
            "keith_fanboy", "7_train_terry", "UncleStevieStan", "barf", "dot"
        ]
        print("\nChecking advocate visibility in Crosstalk Lounge:")
        for adv in advocates:
            found = adv.lower() in body_content.lower()
            status = "✅ Found" if found else "❌ Missing"
            print(f" - {adv}: {status}")
            
        await browser.close()
        
    print(f"\nVerification summary: {len(errors)} errors found.")

if __name__ == "__main__":
    asyncio.run(run())
