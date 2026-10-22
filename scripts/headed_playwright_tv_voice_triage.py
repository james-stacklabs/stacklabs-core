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
        print("🔧 Launching headed Chromium instance in kiosk mode...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=200,  # linger speed for satisfying live observation
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
        
        # 1. Navigate to the Portal Root
        portal_url = "https://localhost:3000/"
        print(f"🌍 Navigating to Root URL: {portal_url}...")
        page.goto(portal_url)
        page.wait_for_timeout(3000)
        
        # Check if auth bypass is active or if we need to log in
        auth_needed = page.locator("#auth-username").is_visible()
        if auth_needed:
            print("🔑 Logging in to system...")
            page.fill("#auth-username", "james")
            page.wait_for_timeout(1000)
            page.fill("#auth-password", "!!Stella1977")
            page.wait_for_timeout(1000)
            page.click("#auth-submit")
            page.wait_for_timeout(3000)
        else:
            print("⚡ Dev/Localhost Auth Bypass detected.")
            
        print("⏳ Waiting for portal synchronization...")
        page.wait_for_selector("text=PROD ENVIRONMENT", timeout=20000)
        page.wait_for_timeout(3000)

        # 2. Sweep to the Voice Heal page
        target_url = "https://localhost:3000/?room=voice"
        print(f"🎙️ Navigating to Voice Heal route: {target_url}...")
        page.goto(target_url)
        page.wait_for_timeout(5000) # Linger so Pilot can see

        # Capture initial state screenshot
        init_shot = os.path.join(artifacts_dir, "tv_voice_heal_init.png")
        page.screenshot(path=init_shot)
        print(f"📸 Captured initial Voice Heal screenshot: {init_shot}")

        # Click the "Inject NL Outage Phrase" button
        print("⚡ Injecting Natural Language Outage phrase...")
        page.click("text=Inject NL Outage Phrase")
        page.wait_for_timeout(5000) # Wait for self-healing action and log output

        # Capture healed state screenshot
        healed_shot = os.path.join(artifacts_dir, "tv_voice_heal_success.png")
        page.screenshot(path=healed_shot)
        print(f"📸 Captured healed state screenshot: {healed_shot}")

        # 3. Sweep to User Management Cockpit
        mgmt_url = "https://localhost:3000/?room=user_mgmt"
        print(f"🧑‍✈️ Navigating to User Management Roster: {mgmt_url}...")
        page.goto(mgmt_url)
        page.wait_for_timeout(6000) # Linger to observe streaks and badges

        # Capture User Management state
        mgmt_shot = os.path.join(artifacts_dir, "tv_user_mgmt_dashboard.png")
        page.screenshot(path=mgmt_shot)
        print(f"📸 Captured User Management screenshot: {mgmt_shot}")

        # 4. Demonstrate mobile-responsive navigation click toggling
        print("📱 Interactive Navbar Dropdown verification...")
        # Toggle FanStack Suite dropdown
        print("  - Toggling FanStack Suite menu")
        page.click("text=FanStack Suite")
        page.wait_for_timeout(3000)
        
        # Toggle System Root Suite dropdown
        print("  - Toggling System Root Suite menu")
        page.click("text=System Root Suite")
        page.wait_for_timeout(3000)

        # Keep browser open for Pilot James to inspect live on the 65" TV
        inspect_seconds = 25
        print(f"👀 Keeping browser window open on HDMI TV for {inspect_seconds} seconds for active Pilot inspection...")
        page.wait_for_timeout(inspect_seconds * 1000)

        context.close()
        browser.close()
        print("🏁 TV UAT sweep completed successfully!")

if __name__ == "__main__":
    run()
