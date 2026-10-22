#!/usr/bin/env python3
"""
StackLabs Retina Dual Visual Twin Capture Utility
Captures 1920x1080 Desktop Twin and 390x844 Mobile Twin of Retina HUD.
Reference: WO0010959 | Invariant 15 (Two-Call Verification) | Invariant 26 (Gandalf UI Craft)
"""

import asyncio
import os
import shutil
import urllib.request
import json
from pathlib import Path
from playwright.async_api import async_playwright

OUT_DIR = Path("/home/james/stacklabs/pilot_drops/screenshots")
UAT_DIR = Path("/home/james/sovereign_inbox/today/uat_screenshots")
ARTIFACT_DIRS = [
    Path("/home/james/.gemini/antigravity-cli/brain/601f9e60-5419-4111-9621-b22508ebfa9c"),
    Path("/home/james/.gemini/antigravity-cli/brain/0c15aab8-ed73-4c6c-b767-62f9c33a3041"),
    Path("/home/james/.gemini/antigravity-cli/brain/5ee9406f-3df3-497b-a14b-5f2b1fc87d0d")
]

def activate_scenario(scenario_key="CONSEN_SYS_4PANEL"):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:3028/api/allocator/query",
            data=json.dumps({"scenario": scenario_key}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            pass
    except Exception as e:
        print(f"[WARN] Failed to activate scenario via API: {e}")

async def capture_twins():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    UAT_DIR.mkdir(parents=True, exist_ok=True)
    for art_dir in ARTIFACT_DIRS:
        try:
            art_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    activate_scenario("CONSEN_SYS_4PANEL")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop Visual Twin (1920x1080)
        print("[CAPTURE] Capturing Desktop Twin (1920x1080)...")
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_desktop = await ctx_desktop.new_page()
        await page_desktop.goto("http://127.0.0.1:3028/", wait_until="domcontentloaded")
        await page_desktop.wait_for_timeout(1000)

        # Trigger parallel arbitration execution to populate all 4 panels
        try:
            btn_run = await page_desktop.wait_for_selector("#btn-run-arbitration", timeout=3000)
            if btn_run:
                print("[EXECUTE] Triggering parallel arbitration on Desktop twin...")
                await btn_run.click()
                await page_desktop.wait_for_selector(".status-danger", timeout=5000)
                await page_desktop.wait_for_timeout(1000)
        except Exception as e:
            print(f"[WARN] Desktop arbitration trigger: {e}")

        desktop_path = OUT_DIR / "retina_desktop_1920x1080.png"
        uat_desktop_path = UAT_DIR / "retina_desktop_1920x1080.png"
        await page_desktop.screenshot(path=str(desktop_path), full_page=False)
        shutil.copy2(desktop_path, uat_desktop_path)
        print(f"[OK] Desktop twin saved to: {desktop_path} & {uat_desktop_path}")
        for art_dir in ARTIFACT_DIRS:
            try:
                shutil.copy2(desktop_path, art_dir / "retina_desktop_1920x1080.png")
            except Exception:
                pass
        await ctx_desktop.close()

        # 2. Mobile Visual Twin (390x844 - iPhone / Pixel standard)
        print("[CAPTURE] Capturing Mobile Twin (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto("http://127.0.0.1:3028/", wait_until="domcontentloaded")
        await page_mobile.wait_for_timeout(1000)

        try:
            btn_run_m = await page_mobile.wait_for_selector("#btn-run-arbitration", timeout=3000)
            if btn_run_m:
                print("[EXECUTE] Triggering parallel arbitration on Mobile twin...")
                await btn_run_m.click()
                await page_mobile.wait_for_selector(".status-danger", timeout=5000)
                await page_mobile.wait_for_timeout(1000)
        except Exception as e:
            print(f"[WARN] Mobile arbitration trigger: {e}")

        mobile_path = OUT_DIR / "retina_mobile_390x844.png"
        uat_mobile_path = UAT_DIR / "retina_mobile_390x844.png"
        await page_mobile.screenshot(path=str(mobile_path), full_page=False)
        shutil.copy2(mobile_path, uat_mobile_path)
        print(f"[OK] Mobile twin saved to: {mobile_path} & {uat_mobile_path}")
        for art_dir in ARTIFACT_DIRS:
            try:
                shutil.copy2(mobile_path, art_dir / "retina_mobile_390x844.png")
            except Exception:
                pass
        await ctx_mobile.close()

        await browser.close()
    print("[SUCCESS] All dual visual twins captured successfully.")

if __name__ == "__main__":
    asyncio.run(capture_twins())
