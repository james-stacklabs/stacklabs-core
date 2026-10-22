from playwright.sync_api import sync_playwright
import time
import os

def run_uat():
    # Make sure output directory exists
    output_dir = "/home/james/stacklabs/uat_screenshots/"
    os.makedirs(output_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Create a browser context with SSL bypass and high resolution
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = context.new_page()
        
        print("=> Navigating to Main Command Center (Port 3016)...")
        page.goto("https://clio.taila01894.ts.net:3016/")
        
        # Wait a bit for React to hydrate/load
        time.sleep(4)
        
        # Check for authentication gate
        if page.locator("#auth-username").count() > 0 or "username" in page.content().lower():
            try:
                print("=> Found authentication gate. Logging in...")
                page.fill("#auth-username", "james")
                page.fill("#auth-password", "!!Stella1977")
                page.click("#auth-submit")
                time.sleep(5)
            except Exception as e:
                print(f"=> Authentication failed: {e}")
                
        # Wait for dashboard hydration
        time.sleep(5)
        page.screenshot(path=os.path.join(output_dir, "command_center_uat.png"), full_page=True)
        print("=> Captured Main Command Center.")

        print("=> Navigating to Persona Console...")
        # Navigate directly to the Persona Console route
        page.goto("https://clio.taila01894.ts.net:3016/?room=persona_console")
        time.sleep(5)
        
        # Check if auth gate is present on the persona console page
        if page.locator("#auth-username").count() > 0:
            try:
                print("=> Found authentication gate on Persona Console. Logging in...")
                page.fill("#auth-username", "james")
                page.fill("#auth-password", "!!Stella1977")
                page.click("#auth-submit")
                time.sleep(5)
            except Exception as e:
                print(f"=> Authentication failed on Persona Console: {e}")

        # Click the first persona card (perspective-1000) to flip it and verify interaction
        try:
           print("=> Attempting to click a persona card to verify flip interaction...")
           card = page.locator(".perspective-1000").first
           card.click(timeout=3000)
           time.sleep(2)
        except Exception as e:
           print("=> Could not click persona card:", e)
           
        page.screenshot(path=os.path.join(output_dir, "persona_console_uat.png"), full_page=True)
        print("=> Captured Persona Console.")
        
        print("=> Navigating to Wildcard Creator...")
        page.goto("https://clio.taila01894.ts.net:3016/?room=wildcard_advocate")
        time.sleep(5)
        page.screenshot(path=os.path.join(output_dir, "wildcard_creator_uat.png"), full_page=True)
        print("=> Captured Wildcard Creator.")
        
        browser.close()

if __name__ == "__main__":
    run_uat()
