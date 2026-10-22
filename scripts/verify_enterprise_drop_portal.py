#!/usr/bin/env python3
"""
Playwright Verification and Visual Twin Capture for WO0010503:
Deploy StackLabs Restricted Enterprise Diligence Drop Portal with 30-Day Magic Key Gate.
"""

import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def run_visual_twins():
    base_url = "http://127.0.0.1:8088"
    mockup_dir = "/home/james/stacklabs/mockups"
    os.makedirs(mockup_dir, exist_ok=True)

    passcode_img = os.path.join(mockup_dir, "pegasus_uat_wo0010503_passcode_gate.png")
    portal_img = os.path.join(mockup_dir, "pegasus_uat_wo0010503_enterprise_drop_portal.png")

    print("[PLAYWRIGHT] Launching Chromium headless...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # --- TWIN 1: PASSCODE GATE (UNAUTHENTICATED) ---
        context1 = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2
        )
        page1 = await context1.new_page()
        print(f"[PLAYWRIGHT] Navigating to {base_url} (unauthenticated)...")
        resp1 = await page1.goto(base_url, wait_until="networkidle", timeout=15000)
        assert resp1.status == 200, f"Expected 200 OK, got {resp1.status}"

        # Assert Passcode Gate UI
        title1 = await page1.title()
        print(f"[PLAYWRIGHT] Passcode Gate Title: {title1}")
        assert "Enterprise Ingress & File Transfer" in title1 or "STACKLABS" in title1

        await page1.wait_for_selector("#passcode", timeout=5000)
        auth_btn = page1.locator("#authBtn")
        assert await auth_btn.is_visible(), "Authenticate Ingress button must be visible"

        print(f"[PLAYWRIGHT] Capturing visual twin: {passcode_img}")
        await page1.screenshot(path=passcode_img, full_page=True)
        await context1.close()

        # --- TWIN 2: DROP PORTAL (AUTHENTICATED VIA MAGIC KEY) ---
        context2 = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2
        )
        page2 = await context2.new_page()
        auth_url = f"{base_url}/?key=rudnicki2026&from=Pawel+Rudnicki"
        print(f"[PLAYWRIGHT] Navigating to {auth_url} (authenticated via magic key)...")
        resp2 = await page2.goto(auth_url, wait_until="networkidle", timeout=15000)
        assert resp2.status == 200, f"Expected 200 OK, got {resp2.status}"

        title2 = await page2.title()
        print(f"[PLAYWRIGHT] Drop Portal Title: {title2}")
        assert "Enterprise Ingress & File Transfer" in title2 or "STACKLABS" in title2

        # Assert dropzone, sender, memo, and submit button
        await page2.wait_for_selector("#dropZone", timeout=5000)
        sender_val = await page2.locator("#sender").input_value()
        print(f"[PLAYWRIGHT] Prefilled sender value: {sender_val}")
        assert sender_val == "Pawel Rudnicki", f"Expected 'Pawel Rudnicki', got: {sender_val}"
        page_text = await page2.content()
        assert "Energy Diligence" not in page_text, "Found leaked 'Energy Diligence' string in page content"
        assert "SECURE VAULT" not in page_text, "Found leaked 'SECURE VAULT' string in page content"
        assert "ENTITY ATTESTED" in page_text, "Missing 'ENTITY ATTESTED' badge in page content"

        submit_btn = page2.locator("#submitBtn")
        assert await submit_btn.is_visible(), "Ingest to Forensic Surveyor button must be visible"

        print(f"[PLAYWRIGHT] Capturing visual twin: {portal_img}")
        await page2.screenshot(path=portal_img, full_page=True)
        today_img = "/home/james/sovereign_inbox/today/verify_wo0010514_entity_attested.png"
        os.makedirs(os.path.dirname(today_img), exist_ok=True)
        await page2.screenshot(path=today_img, full_page=True)
        print(f"[PLAYWRIGHT] Capturing visual twin: {today_img}")
        await context2.close()

        await browser.close()
        print("[PLAYWRIGHT] Visual twin verification complete!")

if __name__ == "__main__":
    asyncio.run(run_visual_twins())
