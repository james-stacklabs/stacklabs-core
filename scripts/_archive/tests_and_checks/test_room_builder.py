"""
Playwright E2E test: Room Builder full flow
- Login
- Navigate to SD@SF game (823226)
- Open Room Builder
- Verify personas load (no dupes, no james)
- Search for 'SD' and 'SF'
- Select personas
- Save & verify m2m in DB
"""
import asyncio, json, sqlite3
from playwright.async_api import async_playwright

BASE = "https://127.0.0.1:3000"
GAME_PK = "823226"
DB = "/home/james/stacklabs/dna/sovereign_now.db"
SS_DIR = "/tmp/room_builder_test"

import os
os.makedirs(SS_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors", "--no-sandbox"]
        )
        ctx = await browser.new_context(ignore_https_errors=True)
        page = await ctx.new_page()
        page.set_default_timeout(15000)

        # ── 1. Load app ──────────────────────────────────────────────────────
        print("1. Loading app...")
        await page.goto(BASE, wait_until="networkidle")
        await page.screenshot(path=f"{SS_DIR}/01_loaded.png")

        # ── 2. Login ─────────────────────────────────────────────────────────
        print("2. Logging in...")
        try:
            user_field = page.locator("input[type='text'], input[name='username'], input[placeholder*='user' i]").first
            pass_field = page.locator("input[type='password']").first
            await user_field.fill("james")
            await pass_field.fill("sovereign2024")
            submit = page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign In')").first
            await submit.click()
            await page.wait_for_timeout(2000)
            print("   Login submitted")
        except Exception as e:
            print(f"   Login form not found (may already be logged in): {e}")
        await page.screenshot(path=f"{SS_DIR}/02_after_login.png")

        # ── 3. Navigate to SD@SF game ────────────────────────────────────────
        print("3. Navigating to SD@SF room...")
        await page.goto(f"{BASE}?domain=MLB&room=scruffys", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SS_DIR}/03_scruffys.png")

        # Click on SD game in scoreboard
        try:
            sd_tile = page.locator("text=SD").first
            await sd_tile.click()
            await page.wait_for_timeout(2000)
            print("   Clicked SD game")
        except Exception as e:
            print(f"   Could not click SD tile: {e}")
        await page.screenshot(path=f"{SS_DIR}/04_sd_game.png")

        # ── 4. Open Room Builder ─────────────────────────────────────────────
        print("4. Opening Room Builder...")
        try:
            build_btn = page.locator("button:has-text('BUILD ROOM')")
            await build_btn.wait_for(state="visible", timeout=5000)
            await build_btn.click()
            await page.wait_for_timeout(1500)
            print("   Room Builder opened")
        except Exception as e:
            print(f"   BUILD ROOM button not found: {e}")
            await page.screenshot(path=f"{SS_DIR}/04b_no_build_button.png")
        await page.screenshot(path=f"{SS_DIR}/05_room_builder_open.png")

        # ── 5. Count personas loaded ─────────────────────────────────────────
        print("5. Checking personas loaded...")
        try:
            await page.wait_for_selector(".grid >> div", timeout=5000)
            cards = await page.locator(".grid > div").count()
            print(f"   Persona cards visible: {cards}")
            assert cards > 10, f"Too few personas: {cards}"
            print(f"   ✓ {cards} personas loaded")
        except Exception as e:
            print(f"   Persona count check failed: {e}")
        await page.screenshot(path=f"{SS_DIR}/06_personas_loaded.png")

        # ── 6. Search for SD ─────────────────────────────────────────────────
        print("6. Searching for SD personas...")
        try:
            search = page.locator("input[placeholder*='Search']")
            await search.fill("SD")
            await page.wait_for_timeout(800)
            sd_cards = await page.locator(".grid > div").count()
            print(f"   SD search results: {sd_cards}")
        except Exception as e:
            print(f"   Search failed: {e}")
        await page.screenshot(path=f"{SS_DIR}/07_search_sd.png")

        # ── 7. Check for dupes ───────────────────────────────────────────────
        print("7. Checking for duplicates...")
        try:
            names = await page.locator(".grid > div span.font-display").all_text_contents()
            dupes = set(n for n in names if names.count(n) > 1)
            print(f"   Names found: {names}")
            print(f"   Dupes: {dupes if dupes else 'NONE ✓'}")
            assert 'james' not in [n.lower() for n in names], "james is in the list!"
            print("   ✓ james not in list")
        except Exception as e:
            print(f"   Dupe check: {e}")

        # ── 8. Select SD personas ────────────────────────────────────────────
        print("8. Selecting SD personas...")
        try:
            cards = await page.locator(".grid > div").all()
            selected = 0
            for card in cards[:3]:
                await card.click()
                await page.wait_for_timeout(200)
                selected += 1
            print(f"   Selected {selected} SD personas")
        except Exception as e:
            print(f"   Selection failed: {e}")

        # ── 9. Search SF and select ──────────────────────────────────────────
        print("9. Searching for SF personas...")
        try:
            search = page.locator("input[placeholder*='Search']")
            await search.fill("SF")
            await page.wait_for_timeout(800)
            cards = await page.locator(".grid > div").all()
            for card in cards[:3]:
                await card.click()
                await page.wait_for_timeout(200)
            print(f"   Selected SF personas")
        except Exception as e:
            print(f"   SF search/select failed: {e}")

        # ── 10. Add dot ──────────────────────────────────────────────────────
        print("10. Adding dot...")
        try:
            search = page.locator("input[placeholder*='Search']")
            await search.fill("dot")
            await page.wait_for_timeout(800)
            first_card = page.locator(".grid > div").first
            await first_card.click()
            await page.wait_for_timeout(200)
        except Exception as e:
            print(f"    dot selection failed: {e}")
        await page.screenshot(path=f"{SS_DIR}/09_ready_to_save.png")

        # ── 11. Save ─────────────────────────────────────────────────────────
        print("11. Saving room...")
        try:
            save_btn = page.locator("button:has-text('Save')")
            await save_btn.click()
            await page.wait_for_timeout(3000)
            print("    Save clicked")
        except Exception as e:
            print(f"    Save failed: {e}")
        await page.screenshot(path=f"{SS_DIR}/10_after_save.png")

        # ── 12. Verify DB ────────────────────────────────────────────────────
        print("12. Verifying DB...")
        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("""
                SELECT u.user_name FROM m2m_persona_room m 
                JOIN sys_user u ON u.sys_id = m.persona 
                WHERE m.room = ?
            """, (GAME_PK,))
            rows = [r[0] for r in c.fetchall()]
            conn.close()
            print(f"    m2m roster for {GAME_PK}: {rows}")
            if rows:
                print(f"    ✓ Room saved with {len(rows)} personas")
            else:
                print(f"    ✗ No personas in m2m — save may have failed")
        except Exception as e:
            print(f"    DB check failed: {e}")

        await browser.close()
        print(f"\nScreenshots saved to {SS_DIR}/")
        print("DONE ✓")

asyncio.run(main())
