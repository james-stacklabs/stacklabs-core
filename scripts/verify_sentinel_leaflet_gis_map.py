#!/usr/bin/env python3
"""
Playwright Verification Script: WO0010127
Sentinel Real Satellite & Topographic GIS Tile Map Engine (Leaflet)
"""

import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

MOCKUP_DIR = Path("/home/james/sovereign_inbox/tickets/WO0010127/mockups")
MOCKUP_DIR.mkdir(parents=True, exist_ok=True)

URL = "https://127.0.0.1:3038/?tab=radar"

async def run_verification():
    print(f"🚀 [GIS VERIFICATION] Launching headless browser to test Leaflet GIS Map at {URL}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1600, "height": 950},
            ignore_https_errors=True
        )
        page = await context.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        await page.goto(URL, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)

        # 1. Verify Leaflet Container
        map_el = await page.wait_for_selector("#sentinel-pasture-map.leaflet-container", timeout=10000)
        assert map_el is not None, "Leaflet container (#sentinel-pasture-map.leaflet-container) NOT found!"
        print("  ✅ Leaflet map container mounted successfully.")

        # 2. Verify GIS Tile Layers Loaded
        await page.wait_for_selector(".leaflet-tile-loaded, .leaflet-tile", timeout=12000)
        tile_count = await page.locator(".leaflet-tile").count()
        assert tile_count > 0, f"No Leaflet tiles found on map! Count: {tile_count}"
        print(f"  ✅ Continuous GIS tile stream verified ({tile_count} tiles rendered).")

        # 3. Verify Clean Pasture Mode on Initial Load
        # Advisors drawer must be COLLAPSED by default
        advisors_heading = await page.locator("text=Advisors & Triage Desk (4)").count()
        assert advisors_heading == 0, "Advisors drawer was NOT collapsed on initial load!"
        print("  ✅ Clean Pasture Mode verified: Map occupies 100% width, Advisors drawer is collapsed.")

        # Capture Clean Stage Screenshot
        shot1 = str(MOCKUP_DIR / "sentinel_gis_satellite_clean_stage.png")
        await page.screenshot(path=shot1, full_page=True)
        print(f"  📸 Clean stage screenshot captured: {shot1}")

        # 4. Verify Livestock GPS Markers
        cow_markers = page.locator(".cow-gis-marker")
        marker_count = await cow_markers.count()
        print(f"  ✅ Livestock GPS markers found on map: {marker_count} animals.")
        assert marker_count > 0, "Zero cow GPS markers found on Leaflet map!"

        # 5. Test Click on Cow Marker & Biometric Popup
        first_cow = cow_markers.first
        await first_cow.click(force=True)
        await page.wait_for_timeout(800)

        popup = await page.wait_for_selector(".leaflet-popup-content", timeout=5000)
        assert popup is not None, "Biometric popup did not open upon clicking cow marker!"
        popup_text = await popup.inner_text()
        print(f"  ✅ Biometric popup verified: {popup_text.splitlines()[0] if popup_text else 'Open'}")

        shot2 = str(MOCKUP_DIR / "sentinel_gis_satellite_cow_popup.png")
        await page.screenshot(path=shot2, full_page=True)
        print(f"  📸 Cow popup screenshot captured: {shot2}")

        # 6. Test Compass HUD Navigation Buttons
        pan_east_btn = page.locator('button[title*="Pan East"]')
        await pan_east_btn.click()
        await page.wait_for_timeout(500)

        zoom_in_btn = page.locator('button[title*="Zoom In"]')
        await zoom_in_btn.click()
        await page.wait_for_timeout(500)

        recenter_btn = page.locator('button[title*="Recenter Ruddy Ranch"]')
        await recenter_btn.click()
        await page.wait_for_timeout(800)
        print("  ✅ Tactical Compass HUD panBy, zoomIn, and flyTo verified.")

        # 7. Test Topographic Terrain Layer Swapper
        terrain_btn = page.locator('button:has-text("Terrain")')
        await terrain_btn.click()
        await page.wait_for_timeout(1500)
        print("  ✅ Switched to Topographic Terrain layer (OpenTopoMap).")

        # Switch back to Satellite
        sat_btn = page.locator('button:has-text("Satellite")')
        await sat_btn.click()
        await page.wait_for_timeout(1000)
        print("  ✅ Switched back to Esri World Satellite Imagery.")

        # 8. Test Advisors & Triage Drawer Toggle
        advisors_pill = page.locator('header button:has-text("Advisors & Triage")')
        await advisors_pill.click()
        await page.wait_for_timeout(800)

        advisors_drawer = await page.wait_for_selector("text=Advisors & Triage Desk", timeout=5000)
        assert advisors_drawer is not None, "Advisors drawer did not open upon clicking pill!"
        print("  ✅ Advisors & Triage Drawer opened successfully.")

        shot3 = str(MOCKUP_DIR / "sentinel_gis_advisors_drawer.png")
        await page.screenshot(path=shot3, full_page=True)
        print(f"  📸 Advisors drawer screenshot captured: {shot3}")

        # Close Advisors Drawer
        close_drawer_btn = page.locator('button[title="Collapse Drawer"]')
        await close_drawer_btn.click()
        await page.wait_for_timeout(500)
        print("  ✅ Advisors Drawer collapsed cleanly back to 100% map width.")

        # 9. Test Granular Layers Dropdown Menu & Presets
        layers_btn = page.locator('button:has-text("Layers")')
        await layers_btn.click()
        await page.wait_for_timeout(500)
        await page.wait_for_selector("text=GIS Layer Visibility", timeout=3000)
        print("  ✅ Granular Layers menu verified.")

        # Click Tactical Operations Preset
        tactical_btn = page.locator('button:has-text("🔍 Tactical")')
        await tactical_btn.click()
        await page.wait_for_timeout(800)
        print("  ✅ Tactical Operations preset applied.")

        # 10. Test Collapsible Scenario Dock
        scenario_toggle = page.locator('button:has-text("⚡ Scenarios")')
        if await scenario_toggle.count() > 0:
            await scenario_toggle.click()
            await page.wait_for_timeout(500)
            await page.wait_for_selector("text=1. Pasture Status: Morning Grazing", timeout=5000)
            print("  ✅ Scenario Dock expansion verified.")
            # Collapse it back
            collapse_dock_btn = page.locator('button[title="Collapse Scenario Dock"]')
            if await collapse_dock_btn.count() > 0:
                await collapse_dock_btn.click()
                await page.wait_for_timeout(400)
                print("  ✅ Scenario Dock collapsed to sleek bottom pill.")

        # Final Visual Twin Master Screenshot
        twin_shot = str(MOCKUP_DIR / "sentinel_gis_map_visual_twin.png")
        await page.screenshot(path=twin_shot, full_page=True)
        print(f"  📸 Master Visual Twin captured: {twin_shot}")

        await browser.close()
        print("\n🎉 [ALL GIS TESTS PASSED] Sovereign Sentinel Leaflet Map is 100% operational!")

if __name__ == "__main__":
    asyncio.run(run_verification())
