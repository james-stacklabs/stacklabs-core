#!/usr/bin/env python3
import sys
import os
import time
from playwright.sync_api import sync_playwright

def run():
    print("📺 Waking up HDMI TV display via DPMS...")
    os.system("DISPLAY=:0 XAUTHORITY=/home/james/.Xauthority xset dpms force on")
    time.sleep(1)

    print("🚀 Initializing headed Chrome browser on DISPLAY=:0 (TV)...")
    os.environ["DISPLAY"] = ":0"
    os.environ["XAUTHORITY"] = "/home/james/.Xauthority"

    artifacts_dir = "/home/james/.gemini/antigravity/brain/c85de819-7c9c-4c89-bb39-ed840ba00dff"
    os.makedirs(artifacts_dir, exist_ok=True)

    with sync_playwright() as p:
        print("🔧 Launching headed Chromium instance...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=150,  # satisfying live observation speed
            args=[
                "--start-maximized",
                "--kiosk",
                "--window-size=3840,2160",
                "--window-position=0,0",
                "--force-device-scale-factor=1.75",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        context = browser.new_context(
            viewport={"width": 3840, "height": 2160},
            ignore_https_errors=True
        )
        
        page = context.new_page()
        
        login_url = "https://localhost:3000/"
        print(f"🌍 Navigating to Root URL: {login_url}...")
        page.goto(login_url)
        page.wait_for_timeout(3000)
        
        # Check if auth bypass was triggered (already on portal dashboard)
        auth_needed = page.locator("#auth-username").is_visible()
        
        if auth_needed:
            print("🔑 Authentication screen detected. Performing login...")
            page.fill("#auth-username", "james")
            page.wait_for_timeout(1000)
            page.fill("#auth-password", "!!Stella1977")
            page.wait_for_timeout(1000)
            page.click("#auth-submit")
            page.wait_for_timeout(3000)
        else:
            print("⚡ Dev/Localhost Auth Bypass detected! Automatically logged in.")
            
        print("⏳ Waiting for portal synchronization...")
        page.wait_for_selector("text=PROD ENVIRONMENT", timeout=20000)
        page.wait_for_timeout(3000)
        
        # Capture Dashboard
        dash_shot = os.path.join(artifacts_dir, "tv_screenshot_dashboard.png")
        page.screenshot(path=dash_shot)
        print(f"📸 Dashboard screenshot captured: {dash_shot}")
        
        # Room UAT sweep targets
        tv_sweeps = [
            {"name": "Playcall Desk", "room": "playcall_desk", "domain": "MLB"},
            {"name": "Persona Center", "room": "persona_center", "domain": "GLOBAL"},
            {"name": "Detractor Mailbag", "room": "hate_mail_inbox", "domain": "GLOBAL"},
            {"name": "Catnip Wars Control Desk", "room": "catnip_wars", "domain": "GLOBAL"},
            {"name": "User Management Registry", "room": "user_mgmt", "domain": "GLOBAL"},
            {"name": "Stack Seeder Console", "room": "stack_seeder", "domain": "GLOBAL"}
        ]
        
        for sweep in tv_sweeps:
            target_url = f"https://localhost:3000/?domain={sweep['domain']}&room={sweep['room']}"
            print(f"📺 Sweep: Navigating to {sweep['name']} ({target_url})...")
            page.goto(target_url)
            page.wait_for_timeout(7000) # Linger for live observation
            
            # Capture UAT screenshot
            shot_path = os.path.join(artifacts_dir, f"tv_screenshot_{sweep['room']}.png")
            page.screenshot(path=shot_path)
            print(f"📸 Captured screenshot: {shot_path}")
            
            # Form interaction for Stack Seeder Console
            if sweep['room'] == 'stack_seeder':
                print("🍕 Filling Bistro Preset fields live on TV...")
                page.select_option("select", "bistro")
                page.wait_for_timeout(3000)
                
                print("⚡ Activating Ingestion Pipeline Tab...")
                page.click("text=⚙️ Ingestion Pipeline")
                page.wait_for_timeout(2000)
                
                print("⚡ Toggling Avatar Generator...")
                checkbox = page.locator('input[type="checkbox"]')
                if not checkbox.is_checked():
                    page.click("text=⚡ Procedurally Forge 4K Character Avatars via Imagen Ingestion Loop")
                page.wait_for_timeout(3000)
        
        print("👀 Keeping the browser window open on your HDMI TV screen for 35 seconds for active pilot inspection...")
        page.wait_for_timeout(35000)
        
        context.close()
        browser.close()
        print("🏁 TV UAT sweep completed successfully!")

if __name__ == "__main__":
    run()
