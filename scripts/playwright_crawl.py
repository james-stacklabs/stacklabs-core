import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/home/james/.gemini/antigravity/brain/42cafb64-fc06-4dd5-9deb-2e628b4ec15b/artifacts"
BASE_URL = "https://clio.taila01894.ts.net"

DOMAINS = ["ROOT", "PORTAL", "CMDB"]
ROOMS = [
    "starter", "claude", "scruffys", "auditor", "pegasus", "uhf_studio", 
    "persona_console", "god_mode", "rom_gallery", "configurator", "log_viewer", 
    "playcall_desk", "tmi_news_desk", "the_skew", "hot_takes", "shatcast_vision", 
    "persona_center", "knowledge_hub", "sow", "courier", "promo_inbox", 
    "nexus_telemetry", "amen_corner", "artifact_gallery", "fanstack_sandbox", 
    "savant_query", "vocal_matrix", "storyboard_deck", "holodex", "edge_dvr", 
    "stream_sniper", "highlight_heist", "live_chat_sniper", "sovereign_css", 
    "factory_dashboard", "aether_vet", "roll_call", "kanban", "dreadnought", 
    "theme_manager", "argus_nexus", "model_arena", "optical_ingest", 
    "user_management", "system_config", "portal_layout"
]

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()

        # Capture base domains
        for domain in DOMAINS:
            print(f"Navigating to DOMAIN_{domain}...")
            try:
                await page.goto(f"{BASE_URL}/?domain={domain}", wait_until="load", timeout=15000)
            except Exception as e:
                print(f"Timeout on DOMAIN_{domain}, capturing anyway: {e}")
            await page.wait_for_timeout(2000)
            screenshot_path = os.path.join(ARTIFACT_DIR, f"domain_{domain.lower()}.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Saved screenshot: {screenshot_path}")

        # Capture all rooms
        for room in ROOMS:
            print(f"Navigating to ROOM_{room}...")
            try:
                await page.goto(f"{BASE_URL}/?room={room}", wait_until="load", timeout=15000)
            except Exception as e:
                print(f"Timeout on ROOM_{room}, capturing anyway: {e}")
            await page.wait_for_timeout(2000)
            screenshot_path = os.path.join(ARTIFACT_DIR, f"room_{room}.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Saved screenshot: {screenshot_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
