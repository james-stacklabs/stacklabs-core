#!/usr/bin/env python3
"""
scripts/verify_wo0010509_flat_black_scrubber_twins.py
Playwright Visual Twin Capture & Multimodal Gemini Cloud Vision ATF Audit for WO0010509.
Enforces Invariant 49 (Gemini 3.8 Flash Visual Sentry Gate) on host Clio.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv("/home/james/stacklabs/.env")

BASE_URL = "http://127.0.0.1:8088"
AUTH_QUERY = "?key=stacklabs2026"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")
TODAY_DIR = Path("/home/james/sovereign_inbox/today")

async def capture_twins():
    MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
    TODAY_DIR.mkdir(parents=True, exist_ok=True)

    dt_drop = MOCKUPS_DIR / "pegasus_uat_wo0010509_drop_dark_desktop.png"
    mb_drop = MOCKUPS_DIR / "pegasus_uat_wo0010509_drop_dark_mobile.png"
    dt_scrubber = MOCKUPS_DIR / "pegasus_uat_wo0010509_scrubber_dark_desktop.png"
    mb_scrubber = MOCKUPS_DIR / "pegasus_uat_wo0010509_scrubber_dark_mobile.png"
    dt_gate = MOCKUPS_DIR / "pegasus_uat_wo0010509_gate_dark_desktop.png"

    print("[PLAYWRIGHT] Launching Chromium headless on Clio metal...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # -------------------------------------------------------------
        # 1. DESKTOP VIEWPORT (1920x1080)
        # -------------------------------------------------------------
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_d = await ctx_desktop.new_page()

        # Gate View
        print(f"[PLAYWRIGHT] Navigating Desktop to Passcode Gate: {BASE_URL}/")
        resp_gate = await page_d.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=15000)
        assert resp_gate.status == 200, f"Expected 200, got {resp_gate.status}"
        await page_d.evaluate("setTheme('dark')")
        await page_d.wait_for_timeout(300)
        await page_d.screenshot(path=str(dt_gate), full_page=False)
        shutil.copy(dt_gate, TODAY_DIR / dt_gate.name)
        print(f"[PLAYWRIGHT] Captured Gate Dark -> {dt_gate}")

        # Drop Portal View
        portal_url = f"{BASE_URL}/{AUTH_QUERY}"
        print(f"[PLAYWRIGHT] Navigating Desktop to Drop Portal: {portal_url}")
        resp = await page_d.goto(portal_url, wait_until="networkidle", timeout=15000)
        assert resp.status == 200, f"Expected 200, got {resp.status}"

        # Ensure Dark Mode
        await page_d.evaluate("setTheme('dark')")
        await page_d.wait_for_timeout(300)

        # Assert DOM Tokens
        content = await page_d.content()
        assert "border-l-[6px]" in content, "Missing signature 6px status spine!"
        assert "rounded-[2px]" in content, "Missing 2014 Material Utility 2px radius!"
        assert "STACKLABS" in content, "Missing brand wordmark STACKLABS!"
        assert "tabBtnDrop" in content, "Missing tabBtnDrop!"
        assert "tabBtnScrubber" in content, "Missing tabBtnScrubber!"
        assert "scrubberPane" in content, "Missing scrubberPane!"

        # A. Desktop Dark Drop View
        print(f"[PLAYWRIGHT] Capturing Desktop Dark Drop View -> {dt_drop}")
        await page_d.screenshot(path=str(dt_drop), full_page=False)
        shutil.copy(dt_drop, TODAY_DIR / dt_drop.name)

        # B. Desktop Dark Scrubber View
        print("[PLAYWRIGHT] Clicking #tabBtnScrubber...")
        await page_d.click("#tabBtnScrubber")
        await page_d.wait_for_timeout(400)

        is_drop_hidden = await page_d.evaluate("document.getElementById('dropPane').classList.contains('hidden')")
        is_scrubber_visible = await page_d.evaluate("!document.getElementById('scrubberPane').classList.contains('hidden')")
        assert is_drop_hidden, "dropPane should be hidden when scrubber tab is selected"
        assert is_scrubber_visible, "scrubberPane should be visible when scrubber tab is selected"

        # Assert Scrubber Interactivity (3-segment pill)
        print("[PLAYWRIGHT] Testing Fluff Switcher Pill clicks...")
        await page_d.click("#fluffBtn100")
        await page_d.wait_for_timeout(200)
        content_100 = await page_d.content()
        assert "OPERATING MARGIN" in content_100, "Missing OPERATING MARGIN in 100% naked ledger"

        await page_d.click("#fluffBtn50")
        await page_d.wait_for_timeout(200)

        print(f"[PLAYWRIGHT] Capturing Desktop Dark Scrubber View -> {dt_scrubber}")
        await page_d.screenshot(path=str(dt_scrubber), full_page=False)
        shutil.copy(dt_scrubber, TODAY_DIR / dt_scrubber.name)

        await ctx_desktop.close()

        # -------------------------------------------------------------
        # 2. MOBILE VIEWPORT (390x844)
        # -------------------------------------------------------------
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            device_scale_factor=2
        )
        page_m = await ctx_mobile.new_page()

        print(f"[PLAYWRIGHT] Navigating Mobile to Drop Portal: {portal_url}")
        await page_m.goto(portal_url, wait_until="networkidle", timeout=15000)
        await page_m.evaluate("setTheme('dark')")
        await page_m.wait_for_timeout(300)

        print(f"[PLAYWRIGHT] Capturing Mobile Dark Drop View -> {mb_drop}")
        await page_m.screenshot(path=str(mb_drop), full_page=False)
        shutil.copy(mb_drop, TODAY_DIR / mb_drop.name)

        print("[PLAYWRIGHT] Clicking #tabBtnScrubber on Mobile...")
        await page_m.click("#tabBtnScrubber")
        await page_m.wait_for_timeout(400)

        print(f"[PLAYWRIGHT] Capturing Mobile Dark Scrubber View -> {mb_scrubber}")
        await page_m.screenshot(path=str(mb_scrubber), full_page=False)
        shutil.copy(mb_scrubber, TODAY_DIR / mb_scrubber.name)

        await ctx_mobile.close()
        await browser.close()

    print("✅ All Playwright visual twins captured successfully.")
    return {
        "drop_desktop": dt_drop,
        "scrubber_desktop": dt_scrubber,
        "drop_mobile": mb_drop,
        "scrubber_mobile": mb_scrubber,
        "gate_desktop": dt_gate
    }

def run_gemini_vision_audit(image_paths):
    """
    Multimodal Gemini Cloud Vision Audit (Invariant 49).
    Uses gemini-3.8-flash via google.genai to audit aesthetic depth, typography, and layout.
    """
    from google import genai
    from google.genai import types
    from PIL import Image

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY missing from environment!")
        sys.exit(1)

    print("\n🔍 [INVARIANT 49] Initializing Google GenAI Client with gemini-3.8-flash...")
    client = genai.Client(api_key=api_key)

    drop_img = Image.open(image_paths["drop_desktop"])
    scrubber_img = Image.open(image_paths["scrubber_desktop"])

    prompt = """
You are the Sovereign OS Visual Sentry enforcing Invariant 49 (Multimodal Cloud Vision ATF Audit Gate) and 2014 Material Utility Card aesthetics on StackLabs web portals.

Inspect these two visual twin screenshots:
Image 1: StackLabs Direct Diligence Drop Portal (File Drop Tab).
Image 2: StackLabs Primary Source Evasion Scrubber (Evasion Scrubber Tab).

Audit the following criteria strictly:
1. THEME & CANVAS DEPTH PARITY:
   - Is the background a deep flat black void (#090A0F) rather than light mode or washed out gray?
   - Is the central card container a distinct matte flat black surface (#0B0D13) with hairline borders (#1E2330)?
   - Are there any un-themed white cards (#FFFFFF) or floating slate-gray containers (#121722) in dark mode? (Must be NO).
2. CONTEXTUAL TOOL GLOW & STATUS SPINE:
   - Does the card feature a prominent 6px left status spine (Emerald green)?
   - Is there an ambient radial ceiling aura visible at the top of the canvas?
3. TYPOGRAPHY HARMONIZATION:
   - Does the typography look clean, crisp, and high-fidelity (Inter heading, JetBrains Mono badges/eyebrows)?
   - Are headings medium-weight with tight tracking rather than bulky aggressive bold?
4. EVASION SCRUBBER VIEWPORT:
   - Does Image 2 clearly show the Evasion Scrubber interface?
   - Does it display the 'PRIMARY SOURCE EVASION SCRUBBER' title, the amber badge 'MODEL CALIBRATION IN PROGRESS • Q4 2026', the 3-segment switcher pill, the telemetry metrics bar (Glaze Density, Physical Anchors, Evasion Score), the crossed-out fluff disclosure box, and the disabled button?

Provide your structured audit findings. Conclude with either:
'VERDICT: PASS' or 'VERDICT: FAIL - [reason]'
"""

    print("[INVARIANT 49] Sending dual visual twins to gemini-3.8-flash for forensic visual evaluation...")
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            "Image 1: Drop Tab Screenshot",
            drop_img,
            "Image 2: Scrubber Tab Screenshot",
            scrubber_img,
            prompt
        ]
    )

    print("\n" + "="*70)
    print("🤖 GEMINI 3.8 FLASH VISUAL AUDIT REPORT:")
    print("="*70)
    print(response.text)
    print("="*70)

    if "VERDICT: PASS" in response.text:
        print("✅ [INVARIANT 49 GATE PASSED] Gemini Cloud Multimodal Vision verified visual parity on metal.")
        return True
    else:
        print("❌ [INVARIANT 49 GATE FAILED] Gemini Vision flagged defects.")
        return False

def main():
    paths = asyncio.run(capture_twins())
    passed = run_gemini_vision_audit(paths)
    if not passed:
        sys.exit(1)
    print("\n🎉 WORK ORDER WO0010509 VERIFICATION COMPLETE ON METAL.")

if __name__ == "__main__":
    main()
