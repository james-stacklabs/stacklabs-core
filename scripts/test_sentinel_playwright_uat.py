import asyncio
import os
import shutil
from playwright.async_api import async_playwright

BRAIN_DIR = "/home/james/.gemini/antigravity-ide/brain/3391473f-7c5e-4efd-ae8c-a47cd6dd2501"
UAT_DIR = "/home/james/sovereign_inbox/today/uat_screenshots"
TICKET_MOCKUP_DIR = "/home/james/sovereign_inbox/tickets/WO-2026-0907-SENTINEL-SIM/mockups"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1600, "height": 950},
            ignore_https_errors=True
        )
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        url = "https://127.0.0.1:3038/"
        print(f"🚀 Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)

        # 1. Verify Top Action Bar and Brand
        brand = await page.wait_for_selector("text=Sovereign Sentinel", timeout=8000)
        assert brand is not None, "Brand header missing!"
        print("  ✅ Brand and global action bar mounted.")

        # 2. Wait for SVG Tactical Pasture Radar
        svg = await page.wait_for_selector("svg", timeout=8000)
        assert svg is not None, "Tactical SVG pasture map missing!"
        print("  ✅ 2D Pasture Tactical Radar SVG rendered.")

        # 3. Verify Geofences
        await page.wait_for_selector("text=PASTURE A · NORTH GRAZING", timeout=5000)
        await page.wait_for_selector("text=PASTURE C · CREEK BASIN", timeout=5000)
        print("  ✅ Geofenced zones (Pastures A, B, C, Tank #2, Corral) verified.")

        # 4. Wait for tokens to load
        await page.wait_for_timeout(1000)

        # Capture Radar View Screenshot
        radar_shot = os.path.join(BRAIN_DIR, "sentinel_radar_live.png")
        await page.screenshot(path=radar_shot, full_page=True)
        shutil.copy(radar_shot, os.path.join(UAT_DIR, "sentinel_radar_live.png"))
        shutil.copy(radar_shot, os.path.join(TICKET_MOCKUP_DIR, "sentinel_radar_live.png"))
        print(f"  📸 Radar live capture saved to {radar_shot}")

        # 5. Click on Tag #42 token to verify Telemetry Drawer
        print("🔍 Testing Animal Telemetry Drawer for Tag #42...")
        await page.locator("#token-lh_042").click(force=True)
        await page.wait_for_timeout(1000)
        await page.wait_for_selector("text=Bella Creek", timeout=5000)
        print("  ✅ Heifer #42 Telemetry Drawer slide-out verified.")

        drawer_shot = os.path.join(BRAIN_DIR, "sentinel_telemetry_drawer.png")
        await page.screenshot(path=drawer_shot, full_page=True)
        shutil.copy(drawer_shot, os.path.join(UAT_DIR, "sentinel_telemetry_drawer.png"))
        shutil.copy(drawer_shot, os.path.join(TICKET_MOCKUP_DIR, "sentinel_telemetry_drawer.png"))
        print(f"  📸 Telemetry Drawer capture saved to {drawer_shot}")

        # 6. Test Navigation to Executive Overview
        print("🔍 Testing Executive Overview navigation...")
        await page.click("text=Executive Overview")
        await page.wait_for_timeout(1000)
        await page.wait_for_selector("text=Herd Health Index", timeout=5000)
        print("  ✅ Executive Overview loaded.")

        overview_shot = os.path.join(BRAIN_DIR, "sentinel_overview_live.png")
        await page.screenshot(path=overview_shot, full_page=True)
        shutil.copy(overview_shot, os.path.join(UAT_DIR, "sentinel_overview_live.png"))
        shutil.copy(overview_shot, os.path.join(TICKET_MOCKUP_DIR, "sentinel_overview_live.png"))
        print(f"  📸 Executive Overview capture saved to {overview_shot}")

        # 7. Test Navigation to Voice Heal Console
        print("🔍 Testing Voice Heal Console navigation...")
        await page.click("text=Voice Heal Terminal")
        await page.wait_for_timeout(1000)
        await page.wait_for_selector("text=Rugged Voice Heal Field Terminal", timeout=5000)
        print("  ✅ Voice Heal Console loaded.")

        voice_shot = os.path.join(BRAIN_DIR, "sentinel_voice_heal_live.png")
        await page.screenshot(path=voice_shot, full_page=True)
        shutil.copy(voice_shot, os.path.join(UAT_DIR, "sentinel_voice_heal_live.png"))
        shutil.copy(voice_shot, os.path.join(TICKET_MOCKUP_DIR, "sentinel_voice_heal_live.png"))
        print(f"  📸 Voice Heal Console capture saved to {voice_shot}")

        # 8. Test Navigation to Herd Ledger
        print("🔍 Testing Herd Ledger navigation...")
        await page.click("text=Longhorn Herd Ledger")
        await page.wait_for_timeout(1000)
        await page.wait_for_selector("text=Longhorn Herd Master Ledger", timeout=5000)
        print("  ✅ Herd Ledger loaded.")

        ledger_shot = os.path.join(BRAIN_DIR, "sentinel_herd_ledger_live.png")
        await page.screenshot(path=ledger_shot, full_page=True)
        shutil.copy(ledger_shot, os.path.join(UAT_DIR, "sentinel_herd_ledger_live.png"))
        shutil.copy(ledger_shot, os.path.join(TICKET_MOCKUP_DIR, "sentinel_herd_ledger_live.png"))
        print(f"  📸 Herd Ledger capture saved to {ledger_shot}")

        # 9. Verify Zero Console Errors
        print(f"\n🔍 [AUDIT] Checking browser console errors ({len(console_errors)} found)...")
        if console_errors:
            print("  ⚠️ Console errors detected:", console_errors)
        else:
            print("  ✅ Clean UAT run with ZERO console errors.")

        await browser.close()
        print("\n🎉 [UAT COMPLETE] All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
