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

    artifacts_dir = "/home/james/.gemini/antigravity/brain/069c7a61-ec64-4f62-a804-ff2d88b99d2d"
    os.makedirs(artifacts_dir, exist_ok=True)

    with sync_playwright() as p:
        print("🔧 Launching headed Chromium instance in kiosk mode...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=200,
            args=[
                "--start-maximized",
                "--kiosk",
                "--window-size=3840,2160",
                "--window-position=0,0",
                "--force-device-scale-factor=1.5",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        context = browser.new_context(
            viewport={"width": 3840, "height": 2160},
            ignore_https_errors=True
        )
        
        # 1. Spite Slice tab (Port 3019)
        print("🍕 Opening Spite Slice on Port 3019...")
        page_spite = context.new_page()
        page_spite.goto("https://localhost:3019/")
        page_spite.wait_for_timeout(3000)
        
        # Click Spite Crew Roster
        print("👉 Clicking Spite Crew Roster to display Barb Greene...")
        page_spite.click("text=Spite Crew Roster")
        page_spite.wait_for_timeout(3000)
        
        # Capture Spite Slice screenshot
        spite_shot = os.path.join(artifacts_dir, "tv_spite_slice_roster.png")
        page_spite.screenshot(path=spite_shot)
        print(f"📸 Captured Spite Slice screenshot: {spite_shot}")
        
        # 2. Card Turpey tab (Port 3016)
        print("🃏 Opening Card Turpey on Port 3016...")
        page_turpey = context.new_page()
        page_turpey.goto("https://localhost:3016/")
        page_turpey.wait_for_timeout(3000)
        
        # Click Advocates Roster
        print("👉 Clicking Advocates Roster to display Sean Carroll...")
        page_turpey.click("text=Advocates Roster")
        page_turpey.wait_for_timeout(3000)
        
        # Capture Card Turpey screenshot
        turpey_shot = os.path.join(artifacts_dir, "tv_card_turpey_roster.png")
        page_turpey.screenshot(path=turpey_shot)
        print(f"📸 Captured Card Turpey screenshot: {turpey_shot}")

        # Infinite loop alternating focus between the two screens so Barb and James can admire them!
        print("🔄 Beginning alternate showcase loop. Press Ctrl+C in terminal to stop.")
        loop_count = 0
        try:
            while True:
                # Bring Spite Slice to front
                print(f"🍕 Loop {loop_count}: Showing Spite Slice (Barb Greene's Pizza Joint)")
                page_spite.bring_to_front()
                page_spite.wait_for_timeout(10000) # Showcase for 10 seconds
                
                # Bring Card Turpey to front
                print(f"🃏 Loop {loop_count}: Showing Card Turpey (Sean Carroll's Sports Showroom)")
                page_turpey.bring_to_front()
                page_turpey.wait_for_timeout(10000) # Showcase for 10 seconds
                
                loop_count += 1
        except KeyboardInterrupt:
            print("🛑 Showcase stopped by keyboard interrupt.")
        finally:
            context.close()
            browser.close()
            print("🏁 Showcase finished.")

if __name__ == "__main__":
    run()
