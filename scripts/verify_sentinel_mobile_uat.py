import asyncio
import os
import shutil
from playwright.async_api import async_playwright

BRAIN_DIR = "/home/james/.gemini/antigravity-cli/brain/58c6e25c-45f3-4fd2-a8d4-1edfbed70d33/uat_screenshots"
UAT_DIR = "/home/james/sovereign_inbox/today/uat_screenshots"
os.makedirs(BRAIN_DIR, exist_ok=True)
os.makedirs(UAT_DIR, exist_ok=True)

async def run_uat():
    async with async_playwright() as p:
        # Emulate Pixel 10a mobile device viewport
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 412, "height": 915},
            user_agent="Mozilla/5.0 (Linux; Android 15; Pixel 10a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
            ignore_https_errors=True,
            has_touch=True
        )
        page = await context.new_page()

        url = "https://127.0.0.1:3038/"
        print(f"🚀 [UAT] Navigating to {url} on mobile viewport (412x915)...")
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)

        # ----------------------------------------------------------------------
        # 1. Header Polish Verification
        # ----------------------------------------------------------------------
        print("\n🔍 1. Verifying Mobile Header Polish...")
        header_text = await page.inner_text("header")
        assert "SOVEREIGN SENTINEL" in header_text, "Header brand missing!"
        assert "📍 Athens, TX · Pasture Live" in header_text, f"Badge missing '📍 Athens, TX · Pasture Live'! Got: {header_text}"
        assert "PROD · Port 3038" not in header_text, "Stale 'PROD · Port 3038' found in header!"
        print("  ✅ Mobile header: Clean 'SOVEREIGN SENTINEL' & '📍 Athens, TX · Pasture Live' badge verified.")

        # ----------------------------------------------------------------------
        # 2. Theme Engine Hardening Verification
        # ----------------------------------------------------------------------
        print("\n🔍 2. Verifying Theme Engine on Mobile Drawer...")
        # Open mobile drawer via hamburger
        await page.click("button[aria-label='Open Navigation Menu']")
        await page.wait_for_timeout(500)

        # Verify theme switcher buttons in mobile drawer
        drawer = page.locator(".lg\\:hidden")
        daylight_btn = drawer.locator("button:has-text('Daylight')")
        night_btn = drawer.locator("button:has-text('Night')")
        rugged_btn = drawer.locator("button:has-text('Rancher')")

        assert await daylight_btn.is_visible(), "Daylight theme button not visible in mobile drawer!"
        
        # Test Daylight Theme
        print("  -> Switching to Sunburst Daylight theme...")
        await daylight_btn.click()
        await page.wait_for_timeout(500)
        theme_html = await page.evaluate("document.documentElement.getAttribute('data-theme')")
        theme_body = await page.evaluate("document.body.getAttribute('data-theme')")
        theme_root = await page.evaluate("document.getElementById('root')?.getAttribute('data-theme')")
        assert theme_html == "sunburst-daylight", f"html data-theme was {theme_html}"
        assert theme_body == "sunburst-daylight", f"body data-theme was {theme_body}"
        assert theme_root == "sunburst-daylight", f"root data-theme was {theme_root}"
        print("  ✅ Daylight theme active on documentElement, body, and #root.")

        # Close drawer and capture Daylight canvas
        await page.click("button[title='Close drawer']")
        await page.wait_for_timeout(500)
        shot_daylight = os.path.join(BRAIN_DIR, "sentinel_mobile_daylight_theme.png")
        await page.screenshot(path=shot_daylight)
        shutil.copy(shot_daylight, os.path.join(UAT_DIR, "sentinel_mobile_daylight_theme.png"))
        print(f"  📸 Daylight theme visual twin saved: {shot_daylight}")

        # Reopen drawer & test Obsidian Night Theme
        await page.click("button[aria-label='Open Navigation Menu']")
        await page.wait_for_timeout(500)
        print("  -> Switching to Obsidian Night theme...")
        await night_btn.click()
        await page.wait_for_timeout(500)
        theme_night = await page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert theme_night == "obsidian-night", f"html data-theme was {theme_night}"
        print("  ✅ Obsidian Night theme active on DOM.")

        await page.click("button[title='Close drawer']")
        await page.wait_for_timeout(500)
        shot_night = os.path.join(BRAIN_DIR, "sentinel_mobile_night_theme.png")
        await page.screenshot(path=shot_night)
        shutil.copy(shot_night, os.path.join(UAT_DIR, "sentinel_mobile_night_theme.png"))
        print(f"  📸 Night theme visual twin saved: {shot_night}")

        # Reopen drawer & restore Rugged theme
        await page.click("button[aria-label='Open Navigation Menu']")
        await page.wait_for_timeout(500)
        await rugged_btn.click()
        await page.wait_for_timeout(500)

        # ----------------------------------------------------------------------
        # 3. Longhorn Herd Roster Mobile Polish Verification
        # ----------------------------------------------------------------------
        print("\n🔍 3. Verifying Longhorn Herd Roster...")
        await page.locator(".lg\\:hidden button:has-text('Longhorn Herd Roster')").click()
        await page.wait_for_timeout(1000)

        # Verify mobile card role="button", tabindex, and 3-column grid
        card = page.locator("div[role='button']").first
        assert await card.is_visible(), "Mobile herd card with role='button' missing!"
        
        metrics_grid = card.locator("div[style*='grid-template-columns']")
        grid_style = await metrics_grid.get_attribute("style")
        assert "repeat(3," in grid_style and "1fr)" in grid_style and "gap: 6px" in grid_style, f"3-column metrics grid missing! Got style: {grid_style}"
        print("  ✅ 3-column metrics grid verified on mobile animal cards.")

        # Tap card to pop open animal detail drawer
        print("  -> Tapping card to inspect Animal Detail Drawer...")
        await card.click()
        await page.wait_for_timeout(800)

        # Verify detail drawer is visible with z-[100]
        modal_container = page.locator("div.fixed.inset-0.z-\\[100\\]").first
        assert await modal_container.is_visible(), "Animal detail modal with z-[100] missing!"
        assert await page.locator("text=Bovine Relational Dossier").is_visible(), "Dossier title missing!"
        print("  ✅ Animal Detail Drawer opened with z-[100] priority elevation.")

        shot_drawer = os.path.join(BRAIN_DIR, "sentinel_mobile_herd_drawer.png")
        await page.screenshot(path=shot_drawer)
        shutil.copy(shot_drawer, os.path.join(UAT_DIR, "sentinel_mobile_herd_drawer.png"))
        print(f"  📸 Animal Detail Drawer visual twin saved: {shot_drawer}")

        # Close detail drawer
        await page.click("button[title='Close dossier']")
        await page.wait_for_timeout(500)

        # ----------------------------------------------------------------------
        # 4. Voice Heal Mobile Touch PTT Verification
        # ----------------------------------------------------------------------
        print("\n🔍 4. Verifying Voice Heal Mobile Touch PTT...")
        await page.click("button[aria-label='Open Navigation Menu']")
        await page.wait_for_timeout(500)
        await page.locator(".lg\\:hidden button:has-text('Field Radio Dispatch')").click()
        await page.wait_for_timeout(1000)

        # Check PTT button attributes
        ptt_btn = page.locator("button:has-text('PRESS & HOLD TO TRANSMIT')")
        assert await ptt_btn.is_visible(), "PTT Walkie-Talkie button missing!"
        btn_style = await ptt_btn.get_attribute("style")
        btn_class = await ptt_btn.get_attribute("class")
        assert "touch-none" in btn_class, "touch-none class missing from PTT button!"
        assert "touch-action: none" in btn_style.lower(), f"touchAction: none missing! Got: {btn_style}"

        # Check HOLD TO TALK and TAP TO TALK button contrast
        hold_btn = page.locator("button:has-text('HOLD TO TALK')")
        hold_style = await hold_btn.get_attribute("style")
        assert "color: rgb(0, 0, 0)" in hold_style or "#000000" in hold_style or "color: #000" in hold_style, f"High contrast color #000000 missing on active HOLD TO TALK! Got: {hold_style}"
        print("  ✅ PTT Touch Handlers, touch-none, touch-action: none, and high-contrast color verified.")

        shot_voice = os.path.join(BRAIN_DIR, "sentinel_mobile_voice_heal.png")
        await page.screenshot(path=shot_voice)
        shutil.copy(shot_voice, os.path.join(UAT_DIR, "sentinel_mobile_voice_heal.png"))
        print(f"  📸 Voice Heal Console visual twin saved: {shot_voice}")

        # ----------------------------------------------------------------------
        # 5. Advisors Desk pt-4 Spacing Verification
        # ----------------------------------------------------------------------
        print("\n🔍 5. Verifying Advisors Desk pt-4 Spacing...")
        await page.click("button[aria-label='Open Navigation Menu']")
        await page.wait_for_timeout(500)
        await page.locator(".lg\\:hidden button:has-text('Advisors & Triage Desk')").click()
        await page.wait_for_timeout(1000)

        turns_container = page.locator("div.flex-1.overflow-y-auto.px-3\\.5.pb-3\\.5.pt-4")
        assert await turns_container.is_visible(), "Advisors Desk dialectic turns container missing pt-4!"
        print("  ✅ Advisors Desk dialectic turns feed has pt-4 padding-top verified.")

        shot_advisors = os.path.join(BRAIN_DIR, "sentinel_mobile_advisors_desk.png")
        await page.screenshot(path=shot_advisors)
        shutil.copy(shot_advisors, os.path.join(UAT_DIR, "sentinel_mobile_advisors_desk.png"))
        print(f"  📸 Advisors Desk visual twin saved: {shot_advisors}")

        # ----------------------------------------------------------------------
        # 6. Argo Pi 5 + AI Hat Live Demo & Camera Ingress Verification
        # ----------------------------------------------------------------------
        print("\n🔍 6. Verifying Argo Pi 5 + AI Hat Optical Ingress...")
        await page.click("button[aria-label='Open Navigation Menu']")
        await page.wait_for_timeout(500)
        await page.locator(".lg\\:hidden button:has-text('Fence & Pasture Cameras')").click()
        await page.wait_for_timeout(1000)

        # Verify Snap Field Photo (Argo AI Hat) button and hidden input
        camera_btn = page.locator("button:has-text('📸 Snap Field Photo (Argo AI Hat)')").last
        assert await camera_btn.is_visible(), "Snap Field Photo (Argo AI Hat) button missing!"
        
        file_input = page.locator("input[type='file'][capture='environment']")
        assert await file_input.count() > 0, "Camera input with capture='environment' missing!"
        print("  ✅ Camera button & capture='environment' input verified.")

        # Trigger Argo Test Scan
        print("  -> Executing live Argo AI Hat edge optical inference...")
        argo_test_btn = page.locator("button:has-text('Argo Test')")
        await argo_test_btn.click()
        await page.wait_for_timeout(1500)

        # Verify optical detection overlay
        argo_badge = page.locator("text=argo · Raspberry Pi 5 + Hailo-10H AI Hat")
        assert await argo_badge.is_visible(), "Argo Edge Node Badge not visible in overlay!"

        # Verify green bounding box
        bounding_box = page.locator("div.border-2.border-emerald-400")
        assert await bounding_box.is_visible(), "Green detection bounding box overlay missing!"

        # Verify work order dispatch banner
        wo_banner = page.locator("text=Field Work Order:")
        assert await wo_banner.is_visible(), "Work Order dispatch banner missing!"
        print("  ✅ Argo Pi 5 AI Hat detection overlay, green bounding box & instant Work Order banner verified.")

        shot_argo = os.path.join(BRAIN_DIR, "sentinel_mobile_argo_ai_hat_overlay.png")
        await page.screenshot(path=shot_argo)
        shutil.copy(shot_argo, os.path.join(UAT_DIR, "sentinel_mobile_argo_ai_hat_overlay.png"))
        print(f"  📸 Argo AI Hat Overlay visual twin saved: {shot_argo}")

        print("\n🎉 [ALL UAT VERIFICATIONS PASSED CLEANLY ON MOBILE VIEWPORT]")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_uat())
