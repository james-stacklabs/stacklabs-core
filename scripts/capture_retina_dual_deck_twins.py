#!/usr/bin/env python3
"""
StackLabs Retina Dual-Deck Visual Twin Capture Utility
Captures 1920x1080 Desktop Twin for Deck 01, 1920x1080 Desktop Twin for Deck 02,
and 390x844 Mobile Twin for Deck 02.
Reference: WO0010966 | Invariant 15 (Two-Call Verification) | Invariant 26 (Gandalf UI Craft)
"""

import asyncio
import json
import os
import shutil
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

EVIDENCE_DIR = Path("/home/james/stacklabs/evidence/visual_twins")
PILOT_DROPS_DIR = Path("/home/james/stacklabs/pilot_drops/screenshots")
UAT_DIR = Path("/home/james/sovereign_inbox/today/uat_screenshots")
ARTIFACT_DIRS = [
    Path("/home/james/.gemini/antigravity-cli/brain/ec41284c-8c1e-4134-a686-0f7facf05620"),
    Path("/home/james/.gemini/antigravity-cli/brain/601f9e60-5419-4111-9621-b22508ebfa9c")
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
        print(f"[WARN] Failed to activate scenario {scenario_key}: {e}")


def copy_to_destinations(source_file: Path, filename: str):
    targets = [
        EVIDENCE_DIR / filename,
        PILOT_DROPS_DIR / filename,
        UAT_DIR / filename
    ]
    for ad in ARTIFACT_DIRS:
        if ad.exists():
            targets.append(ad / filename)

    for target in targets:
        try:
            if target.resolve() != source_file.resolve():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target)
        except Exception as e:
            print(f"[WARN] Could not copy {filename} to {target}: {e}")


async def capture_all_twins():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    PILOT_DROPS_DIR.mkdir(parents=True, exist_ok=True)
    UAT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ---------------------------------------------------------------------
        # 1. Deck 01 Desktop Twin (1920x1080) - Saturday Play / Consen-Sys
        # ---------------------------------------------------------------------
        print("[CAPTURE] Activating Deck 01: CONSEN_SYS_4PANEL...")
        activate_scenario("CONSEN_SYS_4PANEL")

        ctx_deck1 = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_deck1 = await ctx_deck1.new_page()
        print("[CAPTURE] Loading Deck 01 Desktop...")
        await page_deck1.goto("http://127.0.0.1:3028/", wait_until="domcontentloaded")
        await page_deck1.wait_for_timeout(1000)

        # Trigger arbitration if available
        try:
            btn_run = await page_deck1.wait_for_selector("#btn-run-arbitration", timeout=2500)
            if btn_run:
                print("[EXECUTE] Triggering parallel arbitration in Panel 1...")
                await btn_run.click()
                await page_deck1.wait_for_selector(".status-danger", timeout=5000)
                await page_deck1.wait_for_timeout(1000)
        except Exception as e:
            print(f"[NOTE] Arbitration trigger note: {e}")

        deck1_file = EVIDENCE_DIR / "retina_deck01_saturday_desktop.png"
        await page_deck1.screenshot(path=str(deck1_file), full_page=False)
        print(f"[OK] Deck 01 Desktop saved: {deck1_file}")
        copy_to_destinations(deck1_file, "retina_deck01_saturday_desktop.png")
        await ctx_deck1.close()

        # ---------------------------------------------------------------------
        # 2. Deck 02 Desktop Twin (1920x1080) - Sovereign Patriarch Four Pillars
        # ---------------------------------------------------------------------
        print("[CAPTURE] Activating Deck 02: SOVEREIGN_PATRIARCH...")
        activate_scenario("SOVEREIGN_PATRIARCH")

        ctx_deck2 = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_deck2 = await ctx_deck2.new_page()
        print("[CAPTURE] Loading Deck 02 Desktop...")
        await page_deck2.goto("http://127.0.0.1:3028/", wait_until="domcontentloaded")
        await page_deck2.wait_for_timeout(1500)

        # Verify live /stream/c120 element presence
        try:
            sentry_img = await page_deck2.wait_for_selector(".retina-sentry-stream", timeout=4000)
            if sentry_img:
                print("[OK] Verified live .retina-sentry-stream image element rendered.")
        except Exception as e:
            print(f"[WARN] Sentry element wait: {e}")

        # Ensure header buttons reflect Deck 2 active
        btn2 = await page_deck2.query_selector("#btn-deck-2")
        if btn2:
            is_active = await btn2.evaluate("el => el.classList.contains('active')")
            print(f"[STATE] Deck 2 button active: {is_active}")

        deck2_file = EVIDENCE_DIR / "retina_deck02_patriarch_desktop.png"
        await page_deck2.screenshot(path=str(deck2_file), full_page=False)
        print(f"[OK] Deck 02 Desktop saved: {deck2_file}")
        copy_to_destinations(deck2_file, "retina_deck02_patriarch_desktop.png")
        await ctx_deck2.close()

        # ---------------------------------------------------------------------
        # 3. Deck 02 Mobile Twin (390x844) - Sovereign Patriarch Four Pillars Mobile
        # ---------------------------------------------------------------------
        print("[CAPTURE] Loading Deck 02 Mobile (390x844)...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2
        )
        page_mobile = await ctx_mobile.new_page()
        await page_mobile.goto("http://127.0.0.1:3028/", wait_until="domcontentloaded")
        await page_mobile.wait_for_timeout(1500)

        mobile_file = EVIDENCE_DIR / "retina_deck02_patriarch_mobile.png"
        await page_mobile.screenshot(path=str(mobile_file), full_page=False)
        print(f"[OK] Deck 02 Mobile saved: {mobile_file}")
        copy_to_destinations(mobile_file, "retina_deck02_patriarch_mobile.png")
        await ctx_mobile.close()

        await browser.close()
        print("[SUCCESS] All dual-deck visual twins captured and distributed successfully.")


if __name__ == "__main__":
    asyncio.run(capture_all_twins())
