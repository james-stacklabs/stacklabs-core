#!/usr/bin/env python3
import os
import time
import subprocess
from playwright.sync_api import sync_playwright

def run_visual_verification():
    output_dir = "/home/james/stacklabs/uat_screenshots/"
    os.makedirs(output_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = context.new_page()
        
        url = "https://clio.taila01894.ts.net:3010/fan-portal?_game_room=822793"
        print(f"=> Navigating to Watch Room: {url}")
        page.goto(url)
        
        # Wait a bit for React to load and WebSocket to connect
        time.sleep(5)
        
        page.screenshot(path=os.path.join(output_dir, "sports_dashboard_pre_takeover.png"))
        print("=> Captured pre-takeover state.")
        
        # Trigger the takeover overlay
        print("=> Triggering Keith Hernandez Takeover Overlay via script...")
        subprocess.run(["/home/james/stacklabs/.venv/bin/python3", "/home/james/stacklabs/scripts/test_keith_overlay.py"])
        
        # Wait 1.5 seconds for the takeover animation to be mid-transition
        time.sleep(1.5)
        page.screenshot(path=os.path.join(output_dir, "sports_dashboard_during_takeover.png"))
        print("=> Captured during-takeover state.")
        
        # Wait 4 more seconds for the takeover to finish and chat log to be visible
        time.sleep(4.0)
        page.screenshot(path=os.path.join(output_dir, "sports_dashboard_post_takeover.png"))
        print("=> Captured post-takeover state.")
        
        browser.close()

if __name__ == "__main__":
    run_visual_verification()
