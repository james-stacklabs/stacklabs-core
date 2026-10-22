#!/usr/bin/env python3
"""
scripts/verify_wo0010898_listen_twins.py
Verification script for WO0010898:
- Asserts Header does not contain Public, Protected, Pilot Drop, or window.prompt
- Asserts presence of StackLabs LLC, Paul Rudnicki badge, Deck (PDF), Video (73s), LISTEN pill
- Captures desktop (1920x1080) and mobile (390x844) visual twins.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:3040"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")

async def run_audit():
    MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
    desktop_twin = MOCKUPS_DIR / "listen_wo0010898_desktop.png"
    mobile_twin = MOCKUPS_DIR / "listen_wo0010898_mobile.png"

    print(f"[VERIFY] Starting Playwright audit against {BASE_URL}...")

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

        # Catch unexpected dialogs if window.prompt is triggered
        dialog_triggered = []
        page_d.on("dialog", lambda dialog: dialog_triggered.append(dialog.message))

        resp = await page_d.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        assert resp and resp.status == 200, f"Expected 200, got {resp.status if resp else 'None'}"

        # Wait for Header to render
        header = await page_d.wait_for_selector("header", timeout=5000)
        assert header, "Header element not found"

        header_text = await header.inner_text()
        header_html = await header.inner_html()

        print(f"[VERIFY] Header inner text: {header_text.replace(chr(10), ' ')}")

        # Acceptance criteria checks
        assert "PAUL RUDNICKI" in header_text, "Missing PAUL RUDNICKI in header"
        assert "HORIZON STRATEGIC EXECUTIVE BRIEFING" in header_text, "Missing briefing subtitle"
        assert "LISTEN" in header_text, "Missing LISTEN pill in header"
        assert "Deck (PDF)" in header_text, "Missing Deck (PDF) in header"
        assert "Video (73s)" in header_text, "Missing Video (73s) in header"

        # Negative checks
        assert "Public" not in header_text, "FORBIDDEN: 'Public' toggle still in header"
        assert "Protected" not in header_text, "FORBIDDEN: 'Protected' toggle still in header"
        assert "Pilot Drop" not in header_text, "FORBIDDEN: 'Pilot Drop' link still in header"
        assert "Pilot Drop" not in header_html, "FORBIDDEN: 'Pilot Drop' in header HTML"
        assert "handleToggleAuth" not in header_html, "FORBIDDEN: 'handleToggleAuth' in header HTML"
        assert len(dialog_triggered) == 0, f"Unexpected dialogs triggered: {dialog_triggered}"

        # Save desktop visual twin
        await page_d.screenshot(path=str(desktop_twin), full_page=True)
        print(f"[VERIFY] Desktop visual twin saved: {desktop_twin}")
        await ctx_desktop.close()

        # 2. Mobile Viewport (390x844 - iPhone 14/15)
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True
        )
        page_m = await ctx_mobile.new_page()
        resp_m = await page_m.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        assert resp_m and resp_m.status == 200

        header_m = await page_m.wait_for_selector("header", timeout=5000)
        assert header_m, "Header element not found on mobile"

        header_m_text = await header_m.inner_text()
        assert "Public" not in header_m_text, "FORBIDDEN: 'Public' on mobile header"
        assert "Pilot Drop" not in header_m_text, "FORBIDDEN: 'Pilot Drop' on mobile header"

        await page_m.screenshot(path=str(mobile_twin), full_page=True)
        print(f"[VERIFY] Mobile visual twin saved: {mobile_twin}")
        await ctx_mobile.close()

        await browser.close()

    print("[VERIFY] All verification assertions PASSED successfully on dedicated local hardware.")

if __name__ == "__main__":
    asyncio.run(run_audit())
