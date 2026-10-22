import asyncio
import os
import shutil
from playwright.async_api import async_playwright

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

        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        url = "http://127.0.0.1:8095/v6/chat"
        print(f"Navigating to {url} at 390x844...")
        await page.goto(url, wait_until="networkidle")

        # 1. Assert command bar visibility and bounding box
        cmd_bar = page.locator(".command-bar")
        await cmd_bar.wait_for(state="visible")
        box = await cmd_bar.bounding_box()
        assert box is not None, "Command bar bounding box is None!"
        print(f"[ASSERT] Command bar bounding box: y={box['y']}, height={box['height']}, total_bottom={box['y'] + box['height']}")
        assert box['y'] > 700, f"Command bar not pinned to bottom! y={box['y']}"
        assert abs((box['y'] + box['height']) - 844) <= 2, f"Command bar bottom ({box['y'] + box['height']}) not at viewport bottom (844)"

        # 2. Assert wire input and send button
        wire_input = page.locator("#wire-input")
        assert await wire_input.is_visible(), "wire-input is not visible!"
        send_btn = page.locator(".send-btn")
        assert await send_btn.is_visible(), "send-btn is not visible!"

        # 3. Assert status pill and footer are hidden on mobile
        status_pill_display = await page.locator(".status-pill").evaluate("el => window.getComputedStyle(el).display")
        print(f"[ASSERT] status-pill computed display on mobile: {status_pill_display}")
        assert status_pill_display == "none", f"status-pill should be hidden on mobile, got {status_pill_display}"

        footer_display = await page.locator(".terminal-footer").evaluate("el => window.getComputedStyle(el).display")
        print(f"[ASSERT] terminal-footer computed display on mobile: {footer_display}")
        assert footer_display == "none", f"terminal-footer should be hidden on mobile, got {footer_display}"

        # 4. Assert carrier tag content
        carrier_text = await page.locator("#carrier-text").text_content()
        print(f"[ASSERT] carrier-text: {carrier_text}")
        assert "SMYRNA ⇄ PAWEL" in carrier_text, f"Unexpected carrier text: {carrier_text}"

        # 5. Type a test message to ensure interactivity without visual break
        await wire_input.fill("Testing direct mobile wire pin...")
        await asyncio.sleep(0.5)

        # 6. Capture Visual Twin Screenshot
        out_dir = "/home/james/stacklabs/mockups"
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "pegasus_uat_wo0010562_mobile_pinned.png")
        await page.screenshot(path=out_path)
        print(f"[OK] Captured visual twin to {out_path}")

        # Also copy to stacklabs mockups if exists
        stacklabs_mockups = "/home/james/stacklabs/mockups"
        if os.path.exists(stacklabs_mockups):
            shutil.copy2(out_path, os.path.join(stacklabs_mockups, "pegasus_uat_wo0010562_mobile_pinned.png"))
            print(f"[OK] Copied visual twin to {stacklabs_mockups}/pegasus_uat_wo0010562_mobile_pinned.png")

        await browser.close()
        print("[SUCCESS] All mobile viewport pin assertions passed!")

if __name__ == "__main__":
    asyncio.run(run())
