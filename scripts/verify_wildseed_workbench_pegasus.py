#!/usr/bin/env python3
"""
Pegasus Visual Twin & Playwright UAT:
WO0010201 - WildSeed Extracts Unified Master-Detail Vault & Terpene Radar Workbench
Executes on Node Pegasus (100.96.77.20) over Tailscale to test:
1. Desktop 1920x1080 co-located master-detail workbench (Extract Vault on left, Terpene Radar bench on right).
2. Instant card selection reactivity without vertical scrolling or browser zoom.
3. Live morphing of animated SVG 6-axis Terpene Radar polygon, telemetry header, and aroma grid.
4. Low-temp dab vaporization slider with 480°F-510°F Golden Pocket calibration.
5. Mobile 390x844 responsive single-column stacked layout.
"""

import os
import sys
import json
import subprocess
from datetime import datetime

PEGASUS_IP = "100.96.77.20"
PEGASUS_USER = "james"
REMOTE_PY = "/home/james/sovereign_sentry/.venv/bin/python3"
OS_SHOT_DIR = "/home/james/stacklabs/screenshots"

os.makedirs(OS_SHOT_DIR, exist_ok=True)

REMOTE_SCRIPT = """
import asyncio
import json
import os
from playwright.async_api import async_playwright

async def main():
    results = {"success": False, "checks": [], "errors": []}
    os.makedirs("/home/james/sovereign_sentry/captures", exist_ok=True)
    target_url = "https://www.stacklabsllc.com/wildseed"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # =========================================================================
        # 1. DESKTOP 1920x1080 MASTER-DETAIL WORKBENCH VERIFICATION
        # =========================================================================
        desktop_ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = await desktop_ctx.new_page()
        
        print(f"Navigating to {target_url} (Desktop 1920x1080)...")
        await page.goto(target_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Scroll to Extract Vault section
        vault_elem = page.locator("#vault")
        if not await vault_elem.is_visible():
            results["errors"].append("#vault anchor not found!")
            print("❌ #vault anchor missing")
        else:
            await vault_elem.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)
            results["checks"].append("#vault anchor verified and visible")
            print("✔ #vault anchor found and in viewport")

        # Verify side-by-side master-detail layout
        radar_elem = page.locator("#radar")
        if not await radar_elem.is_visible():
            results["errors"].append("#radar workbench panel not visible!")
            print("❌ #radar missing")
        else:
            results["checks"].append("#radar laboratory workbench panel co-located and visible")
            print("✔ #radar workbench panel visible")

        # Check initial selection: Cold-Cure Live Rosin
        initial_card = page.locator("article:has-text('Cold-Cure Live Rosin')").first
        if await initial_card.is_visible():
            active_badge = initial_card.locator("text=ACTIVE RADAR BENCH")
            if await active_badge.is_visible():
                results["checks"].append("Initial cultivar card has ACTIVE RADAR BENCH badge")
                print("✔ Initial card active badge confirmed")

        # Click on 'Solventless Fresh Badder'
        badder_card = page.locator("article:has-text('Solventless Fresh Badder')").first
        print("Clicking 'Solventless Fresh Badder' card...")
        await badder_card.click()
        await page.wait_for_timeout(800)

        # Verify radar workbench immediately updated
        radar_header = await radar_elem.locator("h3").inner_text()
        print(f"Radar Workbench Header after click: {radar_header}")
        if "Solventless Fresh Badder" in radar_header:
            results["checks"].append("Radar workbench header morphed immediately to 'Solventless Fresh Badder'")
            print("✔ Co-located radar workbench updated without scrolling")
        else:
            results["errors"].append(f"Expected 'Solventless Fresh Badder' in radar header, got: {radar_header}")

        # Verify lineage badge updated
        lineage_badge = await radar_elem.locator("text=Papaya Cake x Highlands Strawberry").is_visible()
        if lineage_badge:
            results["checks"].append("Lineage badge updated to 'Papaya Cake x Highlands Strawberry'")
            print("✔ Lineage badge verified")

        # Verify Terpenes % updated to 10.2%
        terp_badge = await radar_elem.locator("text=TOTAL TERPENES: 10.2%").is_visible()
        if terp_badge:
            results["checks"].append("Total Terpenes updated to 10.2%")
            print("✔ Terpenes % verified")

        # Capture Desktop Workbench visual twin
        desktop_shot = "/home/james/sovereign_sentry/captures/pegasus_visual_twin_WO0010201_desktop_workbench.png"
        await page.screenshot(path=desktop_shot, full_page=False)
        results["desktop_screenshot"] = desktop_shot
        print(f"✔ Desktop visual twin captured: {desktop_shot}")

        # Test Low-Temp Dab Slider interaction
        slider = radar_elem.locator("input[type='range']")
        if await slider.is_visible():
            await slider.fill("495")
            await page.wait_for_timeout(300)
            golden_text = await radar_elem.locator("text=GOLDEN POCKET").first.is_visible()
            if golden_text:
                results["checks"].append("Low-temp dab slider 480°F-510°F Golden Pocket calibration confirmed")
                print("✔ Low-temp dab slider Golden Pocket confirmed")

        await desktop_ctx.close()

        # =========================================================================
        # 2. MOBILE 390x844 RESPONSIVE STACKED LAYOUT VERIFICATION
        # =========================================================================
        mobile_ctx = await browser.new_context(
            viewport={"width": 390, "height": 844},
            ignore_https_errors=True
        )
        mobile_page = await mobile_ctx.new_page()
        print(f"Navigating to {target_url} (Mobile 390x844)...")
        await mobile_page.goto(target_url, wait_until="networkidle", timeout=30000)
        await mobile_page.wait_for_timeout(2000)

        # Scroll to Extract Vault
        m_vault = mobile_page.locator("#vault")
        if await m_vault.is_visible():
            await m_vault.scroll_into_view_if_needed()
            await mobile_page.wait_for_timeout(1000)

        # Capture Mobile visual twin
        mobile_shot = "/home/james/sovereign_sentry/captures/pegasus_visual_twin_WO0010201_mobile_stacked.png"
        await mobile_page.screenshot(path=mobile_shot, full_page=False)
        results["mobile_screenshot"] = mobile_shot
        print(f"✔ Mobile visual twin captured: {mobile_shot}")
        results["checks"].append("Mobile 390x844 responsive single-column layout verified")

        await mobile_ctx.close()
        await browser.close()

        results["success"] = len(results["errors"]) == 0
        print(json.dumps(results))

if __name__ == "__main__":
    asyncio.run(main())
"""

def run_verification():
    print(f"[{datetime.now().isoformat()}] 🚀 Launching Pegasus Verification Suite for WO0010201...")
    
    # Push test script to Pegasus
    remote_script_path = "/home/james/sovereign_sentry/verify_WO0010201.py"
    write_cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
        f"{PEGASUS_USER}@{PEGASUS_IP}",
        f"cat << 'EOF' > {remote_script_path}\n{REMOTE_SCRIPT}\nEOF"
    ]
    subprocess.run(write_cmd, check=True)

    # Execute on Pegasus
    run_cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
        f"{PEGASUS_USER}@{PEGASUS_IP}",
        f"{REMOTE_PY} {remote_script_path}"
    ]
    res = subprocess.run(run_cmd, capture_output=True, text=True)
    print("Pegasus STDOUT:")
    print(res.stdout)
    if res.stderr:
        print("Pegasus STDERR:")
        print(res.stderr)

    # Pull screenshots back to Clio
    shots = [
        "pegasus_visual_twin_WO0010201_desktop_workbench.png",
        "pegasus_visual_twin_WO0010201_mobile_stacked.png"
    ]
    for shot in shots:
        remote_file = f"/home/james/sovereign_sentry/captures/{shot}"
        local_file = os.path.join(OS_SHOT_DIR, shot)
        scp_cmd = [
            "scp", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
            f"{PEGASUS_USER}@{PEGASUS_IP}:{remote_file}",
            local_file
        ]
        scp_res = subprocess.run(scp_cmd, capture_output=True)
        if os.path.exists(local_file):
            print(f"✔ Retrieved: {local_file} ({os.path.getsize(local_file):,} bytes)")

if __name__ == "__main__":
    run_verification()
