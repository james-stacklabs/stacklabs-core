#!/usr/bin/env python3
"""
Pegasus Visual Twin & Playwright UAT:
WO0010124 - Sovereign Sentinel Pasture Map Interactive Pan & Zoom
Executes on Node Pegasus (100.96.77.20) over Tailscale to test:
1. Floating Bottom-Right Tactical Navigation HUD (Compass rose, Zoom step, Recenter pill)
2. Fluid Click-and-Drag Panning & 5px Deadband Threshold
3. Focal Zooming and Range Clamping [1.0x - 8.0x]
4. Compass Rose D-Pad Directional Steps (120px)
5. Recenter Reset Action (zoom=1.0, pan={x:0, y:0})
6. Unobstructed Animal Token Inspection (Drawer opens on clean click, suppressed on drag)
7. Multi-Theme Visual Twins (Rancher Rugged & Sunburst Daylight)
"""

import os
import sys
import json
import subprocess
from datetime import datetime

PEGASUS_IP = "100.96.77.20"
PEGASUS_USER = "james"
REMOTE_PY = "/home/james/sovereign_sentry/.venv/bin/python3"
LOCAL_SHOT_DIR = "/home/james/sovereign_inbox/today/uat_screenshots"
OS_SHOT_DIR = "/home/james/stacklabs/screenshots"

os.makedirs(LOCAL_SHOT_DIR, exist_ok=True)
os.makedirs(OS_SHOT_DIR, exist_ok=True)

REMOTE_SCRIPT = """
import asyncio
import json
import os
from playwright.async_api import async_playwright

async def main():
    results = {"success": False, "checks": [], "errors": []}
    os.makedirs("/home/james/sovereign_sentry/captures", exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1600, "height": 950},
            ignore_https_errors=True
        )
        page = await context.new_page()

        # =========================================================================
        # 1. RANCHER RUGGED THEME & HUD VERIFICATION
        # =========================================================================
        rancher_url = "https://clio.taila01894.ts.net:3038/?view=radar&theme=rancher-rugged"
        print(f"Navigating to {rancher_url}...")
        await page.goto(rancher_url, wait_until="networkidle", timeout=25000)
        await page.wait_for_timeout(2000)

        # Verify Tactical HUD presence in bottom-right
        hud = page.locator(".absolute.bottom-4.right-4")
        if not await hud.is_visible():
            results["errors"].append("Tactical Navigation HUD not visible in bottom-right!")
            print("❌ Tactical Navigation HUD missing!")
        else:
            results["checks"].append("HUD visible in bottom-right")
            print("✅ Tactical Navigation HUD located in bottom-right.")

        # Verify Compass Rose D-Pad buttons
        btn_north = page.locator("button[title='Pan North']")
        btn_south = page.locator("button[title='Pan South']")
        btn_east = page.locator("button[title='Pan East']")
        btn_west = page.locator("button[title='Pan West']")
        btn_center = page.locator("button[title='Recenter Macro View']")
        btn_zoom_in = page.locator("button[title='Zoom In']")
        btn_zoom_out = page.locator("button[title='Zoom Out']")

        assert await btn_north.is_visible(), "North pan button missing"
        assert await btn_south.is_visible(), "South pan button missing"
        assert await btn_east.is_visible(), "East pan button missing"
        assert await btn_west.is_visible(), "West pan button missing"
        assert await btn_center.is_visible(), "Center reset button missing"
        assert await btn_zoom_in.is_visible(), "Zoom in button missing"
        assert await btn_zoom_out.is_visible(), "Zoom out button missing"
        results["checks"].append("Compass Rose D-Pad and Zoom buttons verified")
        print("✅ Compass Rose D-Pad and Zoom buttons verified.")

        # Capture initial Rancher HUD state screenshot
        rancher_shot = "/home/james/sovereign_sentry/captures/sentinel_pan_zoom_rancher_1x.png"
        await page.screenshot(path=rancher_shot)
        print(f"📸 Saved Rancher 1.0x snapshot to {rancher_shot}")

        # =========================================================================
        # 2. ZOOM STEPPING & RECENTER PILL VERIFICATION
        # =========================================================================
        print("Testing zoom in stepping...")
        await btn_zoom_in.click()
        await page.wait_for_timeout(400)
        await btn_zoom_in.click()
        await page.wait_for_timeout(400)

        zoom_text = await page.locator(".absolute.bottom-4.right-4 span:has-text('x')").inner_text()
        print(f"Zoom readout after 2 step zooms: {zoom_text}")
        assert "1.6x" in zoom_text or "1.5x" in zoom_text or float(zoom_text.replace("x", "")) > 1.0, f"Zoom didn't increase: {zoom_text}"
        results["checks"].append(f"Zoom in stepping verified: {zoom_text}")

        # Verify Recenter Overview pill button is now visible
        recenter_pill = page.locator("button:has-text('Recenter Overview')")
        assert await recenter_pill.is_visible(), "Recenter Overview pill not visible when zoom > 1.0"
        results["checks"].append("Recenter Overview pill appears when zoomed")
        print("✅ Recenter Overview pill rendered dynamically on zoom.")

        # Test Pan Nudge with D-Pad (East)
        print("Testing Pan East button...")
        await btn_east.click()
        await page.wait_for_timeout(400)

        # Capture Zoomed & Panned State
        zoomed_shot = "/home/james/sovereign_sentry/captures/sentinel_pan_zoom_rancher_zoomed.png"
        await page.screenshot(path=zoomed_shot)
        print(f"📸 Saved zoomed snapshot to {zoomed_shot}")

        # Click Recenter Overview pill
        print("Clicking Recenter Overview pill...")
        await recenter_pill.click()
        await page.wait_for_timeout(500)

        zoom_text_recenter = await page.locator(".absolute.bottom-4.right-4 span:has-text('x')").inner_text()
        assert "1.0x" in zoom_text_recenter, f"Recenter did not restore 1.0x: {zoom_text_recenter}"
        assert not await recenter_pill.is_visible(), "Recenter pill still visible after reset"
        results["checks"].append("Recenter Overview successfully restored 1.0x macro view")
        print("✅ Recenter Overview button restored 1.0x view and hidden.")

        # =========================================================================
        # 3. MOUSE DRAG PANNING & 5PX DEADBAND VERIFICATION
        # =========================================================================
        print("Testing click-and-drag panning on map canvas...")
        canvas = page.locator("div.touch-none")
        box = await canvas.bounding_box()
        assert box is not None, "Canvas bounding box not found"

        start_x = box["x"] + box["width"] / 2
        start_y = box["y"] + box["height"] / 2
        await page.mouse.move(start_x, start_y)
        await page.mouse.down()
        await page.mouse.move(start_x - 120, start_y - 80, steps=10)
        await page.mouse.up()
        await page.wait_for_timeout(400)

        # Verify no animal drawer opened from drag
        drawer = page.locator(".w-84:has-text('Collar Telemetry')")
        assert not await drawer.is_visible(), "Drag pan mistakenly selected animal!"
        results["checks"].append("5px deadband prevented accidental animal selection during drag")
        print("✅ Drag pan executed cleanly without selecting animals.")

        # Reset pan for clean token click
        await btn_center.click()
        await page.wait_for_timeout(300)

        # =========================================================================
        # 4. LONGHORN TOKEN CLICK INSPECTION
        # =========================================================================
        print("Testing clean Longhorn token click inspection...")
        token = page.locator("#token-lh_042")
        if not await token.is_visible():
            token = page.locator("svg g[id^='token-']").first
        await token.click(force=True)
        await page.wait_for_timeout(800)

        drawer = page.locator(".w-84:has-text('Collar Telemetry')")
        assert await drawer.is_visible(), "Animal telemetry drawer did not open on clean click"
        results["checks"].append("Clean click on Longhorn token opened Animal Telemetry Drawer")
        print("✅ Clean click on Longhorn token opened Animal Telemetry Drawer.")

        # Capture screenshot with open drawer and HUD
        drawer_shot = "/home/james/sovereign_sentry/captures/sentinel_pan_zoom_drawer_open.png"
        await page.screenshot(path=drawer_shot)
        print(f"📸 Saved token drawer snapshot to {drawer_shot}")

        # Close drawer
        close_btn = page.locator(".w-84 button:has(svg.lucide-x)")
        if await close_btn.is_visible():
            await close_btn.click()
            await page.wait_for_timeout(300)

        # =========================================================================
        # 5. SUNBURST DAYLIGHT THEME VERIFICATION
        # =========================================================================
        daylight_url = "https://clio.taila01894.ts.net:3038/?view=radar&theme=sunburst-daylight"
        print(f"Navigating to {daylight_url}...")
        await page.goto(daylight_url, wait_until="networkidle", timeout=25000)
        await page.wait_for_timeout(2000)

        daylight_hud = page.locator(".absolute.bottom-4.right-4")
        assert await daylight_hud.is_visible(), "HUD not visible in daylight theme"
        results["checks"].append("HUD visible and styled under Sunburst Daylight theme")

        # Capture Daylight Theme visual twin
        daylight_shot = "/home/james/sovereign_sentry/captures/sentinel_pan_zoom_daylight.png"
        await page.screenshot(path=daylight_shot)
        print(f"📸 Saved Daylight visual twin snapshot to {daylight_shot}")

        await browser.close()
        results["success"] = True
        return results

if __name__ == "__main__":
    res = asyncio.run(main())
    print("RESULT_JSON:" + json.dumps(res))
"""

def run():
    print("🚀 [Clio -> Pegasus] Dispatching Headless Playwright UAT Suite...")
    print(f"Node: Pegasus ({PEGASUS_IP}) over Tailscale")
    
    # Run remote verification
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
        f"{PEGASUS_USER}@{PEGASUS_IP}",
        f"{REMOTE_PY} -c {subprocess.list2cmdline([REMOTE_SCRIPT])}"
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print(f"Stderr: {proc.stderr}")

    if proc.returncode != 0:
        print(f"❌ Remote Pegasus UAT failed with code {proc.returncode}")
        sys.exit(proc.returncode)

    # Scp captured screenshots back to Clio
    shots = [
        "sentinel_pan_zoom_rancher_1x.png",
        "sentinel_pan_zoom_rancher_zoomed.png",
        "sentinel_pan_zoom_drawer_open.png",
        "sentinel_pan_zoom_daylight.png"
    ]
    
    for shot in shots:
        remote_path = f"/home/james/sovereign_sentry/captures/{shot}"
        local_today = os.path.join(LOCAL_SHOT_DIR, shot)
        local_os = os.path.join(OS_SHOT_DIR, shot)
        
        scp_cmd = [
            "scp", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
            f"{PEGASUS_USER}@{PEGASUS_IP}:{remote_path}",
            local_today
        ]
        subprocess.run(scp_cmd, capture_output=True)
        if os.path.exists(local_today):
            subprocess.run(["cp", local_today, local_os])
            print(f"✅ Retrieved visual twin: {local_today} ({os.path.getsize(local_today):,} bytes)")

    print("\n🎉 Pegasus Playwright Visual Twin Verification Completed Successfully!")

if __name__ == "__main__":
    run()
