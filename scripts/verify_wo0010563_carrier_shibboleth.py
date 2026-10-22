#!/usr/bin/env python3
import asyncio
import os
import shutil
import sys
from pathlib import Path
from playwright.async_api import async_playwright

PROJECT_ROOT = Path("/home/james/stacklabs")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from scripts.core import api_client

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()

        url = "http://127.0.0.1:8095/v6/chat"
        print(f"Navigating to {url} at 390x844...")
        await page.goto(url, wait_until="networkidle")

        # 1. Assert carrier tag text
        carrier_text = await page.locator("#carrier-text").text_content()
        print(f"[ASSERT] carrier-text: '{carrier_text}'")
        assert "JAMES ⇄ PAWEL" in carrier_text, f"Unexpected carrier text: {carrier_text}"

        # 2. Assert stream box empty placeholder
        stream_text = await page.locator("#stream-box").text_content()
        print(f"[ASSERT] stream-box text: '{stream_text.strip()}'")
        assert "JAMES ⇄ PAWEL" in stream_text, f"Expected JAMES ⇄ PAWEL in placeholder, got: {stream_text}"

        # 3. Assert command bar is visible and pinned
        cmd_bar = page.locator(".command-bar")
        assert await cmd_bar.is_visible(), "Command bar is not visible!"
        box = await cmd_bar.bounding_box()
        assert box is not None and box['y'] > 700, "Command bar not pinned to bottom!"

        # 4. Capture Visual Twin Screenshot
        out_dir = "/home/james/stacklabs/mockups"
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "pegasus_uat_wo0010563_james_pawel.png")
        await page.screenshot(path=out_path)
        print(f"[OK] Captured visual twin to {out_path}")

        # Also copy to SovereignOS mockups
        sov_mockups = "/home/james/stacklabs/mockups"
        if os.path.exists(sov_mockups):
            shutil.copy2(out_path, os.path.join(sov_mockups, "pegasus_uat_wo0010563_james_pawel.png"))

        # Attach visual twin to ticket WO0010563 via API
        try:
            print("[INFO] Uploading visual twin attachment to WO0010563...")
            upload_res = api_client.upload_ticket_attachment(
                "WO0010563",
                out_path,
                filename="pegasus_uat_wo0010563_james_pawel.png",
                description="Live Pegasus Playwright Visual Twin mobile viewport 390x844 showing JAMES ⇄ PAWEL shibboleth"
            )
            print(f"[OK] Uploaded attachment: {upload_res}")
        except Exception as e:
            print(f"[WARNING] Attachment upload: {e}")

        await browser.close()
        print("[SUCCESS] All carrier shibboleth assertions passed!")

if __name__ == "__main__":
    asyncio.run(run())
