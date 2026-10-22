#!/usr/bin/env python3
"""
scripts/verify_wo0010952_retina_syndicate_shutter.py
Verification script for WO0010952:
- Verifies /api/cam/status, /api/cam/toggle, /api/cam/kill, /api/cam/start endpoints
- Verifies /data/hud.json configuration for syndicate_card and enable_shutter_toggle
- Performs Playwright DOM and visual twin audits (Desktop 1920x1080, Mobile 390x844)
- Captures visual twin screenshots into /home/james/stacklabs/mockups/
"""

import asyncio
import json
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:3028"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")

def verify_shutter_api():
    print("[VERIFY API] Testing Camera Privacy Shutter Endpoints...")
    
    # 1. Reset to open / streaming
    req = urllib.request.Request(f"{BASE_URL}/api/cam/start")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        d = json.loads(resp.read().decode())
        assert d.get("shutter_closed") is False
        assert d.get("status") == "STREAMING"

    # 2. Check status
    req = urllib.request.Request(f"{BASE_URL}/api/cam/status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        d = json.loads(resp.read().decode())
        assert d.get("shutter_closed") is False
        assert d.get("status") == "NOMINAL"

    # 3. Kill switch
    req = urllib.request.Request(f"{BASE_URL}/api/cam/kill")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        d = json.loads(resp.read().decode())
        assert d.get("shutter_closed") is True
        assert d.get("status") == "KILL"

    # 4. Status reflects closed
    req = urllib.request.Request(f"{BASE_URL}/api/cam/status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        d = json.loads(resp.read().decode())
        assert d.get("shutter_closed") is True

    # 5. Toggle switch back to open
    req = urllib.request.Request(f"{BASE_URL}/api/cam/toggle")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        d = json.loads(resp.read().decode())
        assert d.get("shutter_closed") is False
        assert d.get("status") == "TOGGLED"

    print("[VERIFY API] PASS: Shutter API endpoints respond correctly.")

def verify_hud_schema():
    print("[VERIFY SCHEMA] Testing /data/hud.json configuration...")
    url = f"{BASE_URL}/data/hud.json"
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        hud = json.loads(resp.read().decode())

    containers = hud.get("containers", {})
    top_left = containers.get("top_left", {})
    assert top_left.get("enable_shutter_toggle") is True, "top_left missing enable_shutter_toggle"

    top_right = containers.get("top_right", {})
    assert top_right.get("primitive") == "syndicate_card", f"top_right primitive is {top_right.get('primitive')}"
    
    sammy = top_right.get("sammy", {})
    assert "FADING THE .5 HOOK" in sammy.get("quant_lock", ""), f"Unexpected sammy quant lock: {sammy}"

    metsy = top_right.get("metsy", {})
    assert "METSY THE SENTINEL" in metsy.get("operative", ""), f"Unexpected metsy operative: {metsy}"
    assert metsy.get("avatar") == "/media/catnip_cartel.png", f"Unexpected metsy avatar: {metsy}"

    print("[VERIFY SCHEMA] PASS: HUD JSON configuration contains syndicate_card and shutter toggle.")

async def run_visual_audit():
    MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
    desktop_twin = MOCKUPS_DIR / "retina_wo0010952_desktop.png"
    desktop_shutter_twin = MOCKUPS_DIR / "retina_wo0010952_desktop_shutter.png"
    mobile_twin = MOCKUPS_DIR / "retina_wo0010952_mobile.png"

    print(f"[VERIFY PLAYWRIGHT] Starting browser audit against {BASE_URL}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # 1. Desktop Viewport (1920x1080)
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_d = await ctx_desktop.new_page()

        resp = await page_d.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
        assert resp and resp.status == 200, f"Expected 200, got {resp.status if resp else 'None'}"

        # Wait for syndicate card to render in top_right
        await page_d.wait_for_selector(".syndicate-grid", timeout=5000)
        
        # Verify Sammy and Metsy tags
        sammy_tag = await page_d.text_content(".sammy-tag")
        assert "CIT-004 // SAMMY THE SAVANT" in sammy_tag, f"Unexpected sammy tag: {sammy_tag}"

        metsy_tag = await page_d.text_content(".metsy-tag")
        assert "SMYRNA CARTEL // METSY & SAM" in metsy_tag, f"Unexpected metsy tag: {metsy_tag}"

        quant_lock = await page_d.text_content("#sammy-lock-top_right")
        assert "FADING THE .5 HOOK" in quant_lock, f"Unexpected quant lock: {quant_lock}"

        # Verify shutter button exists
        shutter_btn = await page_d.wait_for_selector(".shutter-toggle-btn", timeout=5000)
        assert shutter_btn, "shutter-toggle-btn not found"
        btn_text = await shutter_btn.text_content()
        assert btn_text.strip() == "SHUTTER", f"Expected SHUTTER, got {btn_text}"

        # Wait 1s for layout stabilization and take desktop screenshot (open shutter)
        await asyncio.sleep(1.0)
        await page_d.screenshot(path=str(desktop_twin), full_page=True)
        print(f"[VERIFY PLAYWRIGHT] Desktop screenshot captured -> {desktop_twin}")

        # Click shutter button to close shutter
        await shutter_btn.click()
        await asyncio.sleep(0.5)
        btn_text_closed = await shutter_btn.text_content()
        assert btn_text_closed.strip() == "OPEN CAM", f"Expected OPEN CAM after click, got {btn_text_closed}"

        # Take desktop screenshot with shutter engaged
        await asyncio.sleep(0.5)
        await page_d.screenshot(path=str(desktop_shutter_twin), full_page=True)
        print(f"[VERIFY PLAYWRIGHT] Desktop shutter screenshot captured -> {desktop_shutter_twin}")

        # Click again to restore open camera
        await shutter_btn.click()
        await asyncio.sleep(0.5)
        btn_text_open = await shutter_btn.text_content()
        assert btn_text_open.strip() == "SHUTTER", f"Expected SHUTTER after restoring, got {btn_text_open}"

        # 2. Mobile Viewport (390x844)
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1
        )
        page_m = await ctx_mobile.new_page()
        await page_m.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
        await page_m.wait_for_selector(".syndicate-grid", timeout=5000)
        await asyncio.sleep(0.5)
        await page_m.screenshot(path=str(mobile_twin), full_page=True)
        print(f"[VERIFY PLAYWRIGHT] Mobile screenshot captured -> {mobile_twin}")

        await browser.close()

if __name__ == "__main__":
    verify_shutter_api()
    verify_hud_schema()
    asyncio.run(run_visual_audit())
    print("[VERIFY] ALL VERIFICATION CRITERIA PASSED.")
