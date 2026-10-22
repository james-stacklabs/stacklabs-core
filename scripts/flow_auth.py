from playwright.sync_api import sync_playwright
import time
import os

STATE_FILE = "flow_state.json"
FLOW_URL = "https://aitestkitchen.withgoogle.com/tools/video-fx" # Typical Google Flow / VideoFX URL

def authenticate():
    print("Launching headed browser for manual login...")
    with sync_playwright() as p:
        # Launch headed with anti-bot detection flags disabled
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"]
        )
        context = browser.new_context()
        page = context.new_page()
        
        print(f"Navigating to {FLOW_URL}...")
        page.goto(FLOW_URL)
        
        print("\n*** ACTION REQUIRED ***")
        print("1. Please log in using your Google account.")
        print("2. Navigate to your Wrexham Hot Take project/collection.")
        print("3. Once you are fully logged in and looking at the project, come back here.")
        
        input("\nPress Enter here ONLY AFTER you have fully logged in and loaded the project...")
        
        # Save the authentication state (cookies, local storage, etc.)
        context.storage_state(path=STATE_FILE)
        print(f"\nSuccess! Session state saved to {STATE_FILE}.")
        print("You can now close the browser. The headless script will use this file to bypass login.")
        
        browser.close()

if __name__ == "__main__":
    authenticate()
