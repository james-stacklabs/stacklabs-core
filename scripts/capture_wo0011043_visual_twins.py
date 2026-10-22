#!/usr/bin/env python3
"""
WO0011043 Visual Twin Capture Utility
Captures Desktop (1920x1080) and Mobile (390x844) visual twins of CMDB Studio Port 3025
displaying the Pepe Silvia Dynamic CI Relationship Mesh Canvas, real-time Bézier rewire,
and Live Shootout Arena toggle integration.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT_DIRS = [
    Path("/home/james/stacklabs/walkthroughs/screenshots"),
    Path("/home/james/stacklabs/pilot_drops/screenshots"),
]

async def capture_twins():
    for d in OUT_DIRS:
        d.mkdir(parents=True, exist_ok=True)

    target_url = "http://127.0.0.1:3025/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop Visual Twin - Pepe Silvia Mesh via Dedicated Tab (1920x1080)
        print("[CAPTURE] Capturing Desktop Pepe Silvia Mesh (Initial State)...")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_desktop = await ctx_desktop.new_page()
        await page_desktop.goto(target_url, wait_until="networkidle")
        await page_desktop.wait_for_timeout(1000)

        # Click top nav 'Pepe Silvia Mesh'
        pepe_tab = page_desktop.get_by_role("button", name="Pepe Silvia Mesh", exact=True)
        assert await pepe_tab.count() > 0, "Missing 'Pepe Silvia Mesh' top navigation button"
        await pepe_tab.click()
        await page_desktop.wait_for_timeout(500)

        # Verify board title and status pills
        title_loc = page_desktop.locator("text=Pepe Silvia CI Relationship Board")
        assert await title_loc.count() > 0, "Missing Pepe Silvia Board Title"
        print("[VERIFY] Pepe Silvia Board confirmed mounted!")

        for d in OUT_DIRS:
            await page_desktop.screenshot(path=str(d / "wo0011043_pepe_silvia_initial_desktop.png"), full_page=False)

        # 2. Trigger Real-time Symlink Rewire
        print("[ACTION] Clicking 'Execute Topology Rewire'...")
        rewire_btn = page_desktop.locator("button:has-text('Execute Topology Rewire')")
        assert await rewire_btn.count() > 0, "Missing 'Execute Topology Rewire' button"
        await rewire_btn.click()
        await page_desktop.wait_for_timeout(600)  # Wait for animation and state update

        # Verify rewired state: Reset Topology Mesh button appears
        reset_btn = page_desktop.locator("button:has-text('Reset Topology Mesh')")
        assert await reset_btn.count() > 0, "Missing 'Reset Topology Mesh' button after rewire"
        print("[VERIFY] Real-time symlink rewire executed and verified!")

        for d in OUT_DIRS:
            await page_desktop.screenshot(path=str(d / "wo0011043_pepe_silvia_rewired_desktop.png"), full_page=False)
            await page_desktop.screenshot(path=str(d / "wo0011043_pepe_silvia_rewired_desktop_full.png"), full_page=True)

        # 3. Test Embedded Toggle inside Live Shootout Arena
        print("[ACTION] Navigating to Shootout Arena and toggling Pepe Silvia Mesh...")
        arena_tab = page_desktop.locator("button:has-text('Shootout Arena')")
        await arena_tab.click()
        await page_desktop.wait_for_timeout(500)

        toggle_mesh_btn = page_desktop.locator("button:has-text('Show Pepe Silvia Mesh')")
        assert await toggle_mesh_btn.count() > 0, "Missing 'Show Pepe Silvia Mesh' toggle in Arena"
        await toggle_mesh_btn.click()
        await page_desktop.wait_for_timeout(500)

        for d in OUT_DIRS:
            await page_desktop.screenshot(path=str(d / "wo0011043_arena_embedded_pepe_mesh_desktop.png"), full_page=False)

        # 4. Mobile Visual Twin (390x844)
        print("[CAPTURE] Capturing Mobile Twin (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto(target_url, wait_until="networkidle")
        await page_mobile.wait_for_timeout(1000)

        # Switch to Pepe Silvia Mesh
        pepe_tab_m = page_mobile.get_by_role("button", name="Pepe Silvia Mesh", exact=True)
        if await pepe_tab_m.count() > 0:
            await pepe_tab_m.click()
            await page_mobile.wait_for_timeout(500)

        for d in OUT_DIRS:
            await page_mobile.screenshot(path=str(d / "wo0011043_pepe_silvia_mobile.png"), full_page=False)

        await browser.close()
        print("[DONE] All Visual Twins captured successfully.")

if __name__ == "__main__":
    asyncio.run(capture_twins())
