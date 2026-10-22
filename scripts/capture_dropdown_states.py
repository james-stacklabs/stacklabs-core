import asyncio
import os
import time
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/home/james/sovereign_inbox/uat_screenshots"

async def run():
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()

        print("=> Navigating to Fan Portal (Port 3010)...")
        await page.goto("https://clio.taila01894.ts.net:3010/fan-portal?_game_room=824904", wait_until="load", timeout=30000)
        
        # Wait a bit for React to hydrate/load
        await page.wait_for_timeout(5000)
        
        # Check for authentication gate
        if await page.locator("#auth-username").count() > 0:
            try:
                print("=> Found authentication gate. Logging in...")
                await page.fill("#auth-username", "james")
                await page.fill("#auth-password", "!!Stella1977")
                await page.click("#auth-submit")
                await page.wait_for_timeout(5000)
            except Exception as e:
                print(f"=> Authentication failed: {e}")
        
        # Define the modes and themes to cycle through
        modes = ["Matchup Focus", "Lounge", "Analytics", "Gameday Sim", "Pennant Race"]
        themes = ["sovereign-cyan", "retro-16bit", "the-show-sim", "sny-cinematic", "muppet-hell"]
        
        # Capture default page state
        screenshot_path = os.path.join(ARTIFACT_DIR, "state_default_cinematic.png")
        await page.screenshot(path=screenshot_path)
        print(f"Captured default state to {screenshot_path}")

        # Capture Muppet Hell theme with Matchup Focus mode
        print("=> Changing theme to Muppet Hell...")
        await page.select_option('span:has-text("THEME:") + select', "muppet-hell")
        await page.wait_for_timeout(2000)
        screenshot_path = os.path.join(ARTIFACT_DIR, "state_matchup_muppet_hell.png")
        await page.screenshot(path=screenshot_path)
        print(f"Captured Muppet Hell state to {screenshot_path}")
        
        # Change theme back to SNY Cinematic to test modes
        print("=> Changing theme to SNY Cinematic...")
        await page.select_option('span:has-text("THEME:") + select', "sny-cinematic")
        await page.wait_for_timeout(1000)

        # Loop through all modes with SNY Cinematic
        for mode in modes:
            print(f"=> Selecting mode: {mode}")
            try:
                await page.select_option('span:has-text("MODE:") + select', mode)
                await page.wait_for_timeout(2000)
                
                safe_mode_name = mode.lower().replace(" ", "_")
                screenshot_path = os.path.join(ARTIFACT_DIR, f"state_mode_{safe_mode_name}_cinematic.png")
                await page.screenshot(path=screenshot_path)
                print(f"Captured mode {mode} to {screenshot_path}")
            except Exception as e:
                print(f"Could not select mode {mode}: {e}")

        # Loop through all themes with Matchup Focus mode
        print("=> Resetting mode to Matchup Focus...")
        try:
            await page.select_option('span:has-text("MODE:") + select', "Matchup Focus")
            await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Could not reset mode: {e}")
        
        for theme in themes:
            print(f"=> Selecting theme: {theme}")
            try:
                await page.select_option('span:has-text("THEME:") + select', theme)
                await page.wait_for_timeout(2000)
                
                safe_theme_name = theme.lower().replace("-", "_")
                screenshot_path = os.path.join(ARTIFACT_DIR, f"state_theme_{safe_theme_name}.png")
                await page.screenshot(path=screenshot_path)
                print(f"Captured theme {theme} to {screenshot_path}")
            except Exception as e:
                print(f"Could not select theme {theme}: {e}")

        await browser.close()
        print("=> All screenshots captured successfully.")

if __name__ == "__main__":
    asyncio.run(run())
