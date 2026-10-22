import asyncio
from playwright.async_api import async_playwright
import os

async def run_uat():
    print("🚀 Initializing Playwright Headless UAT for Particle Cannon & Generative HoloDex...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--ignore-certificate-errors",
                "--allow-insecure-localhost"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1600, "height": 900},
            ignore_https_errors=True
        )
        
        page = await context.new_page()
        await page.add_init_script("""
            sessionStorage.setItem('sov_auth', 'unlocked');
            localStorage.setItem('sovereign_session_token', 'pilot_omega_valid');
            localStorage.setItem('sovereign_user_name', 'james');
            localStorage.setItem('sovereign_role', 'pilot');
        """)
        
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        url = "https://clio.taila01894.ts.net:3016/?room=particle_lab&vip=creator"
        print(f"📡 Navigating to: {url}")
        
        await page.goto(url, wait_until="networkidle", timeout=20000)
        await page.wait_for_selector("text=Sovereign Particle Accelerator", timeout=10000)
        await asyncio.sleep(2)
        
        os.makedirs("/home/james/sovereign_inbox/today/uat_screenshots", exist_ok=True)
        
        # 1. Switch to Blaster Gun mode and fire
        print("🔫 Selecting Particle Cannon / Blaster Gun mode...")
        gun_btn = page.locator("button:has-text('Blaster Gun')")
        await gun_btn.click()
        await asyncio.sleep(1)
        
        # Click and drag on canvas to fire continuous stream
        canvas = page.locator("canvas")
        box = await canvas.bounding_box()
        if box:
            await page.mouse.move(box["x"] + box["width"] * 0.7, box["y"] + box["height"] * 0.4)
            await page.mouse.down()
            await asyncio.sleep(1.5)
            await page.mouse.up()
            
        cannon_shot = "/home/james/sovereign_inbox/today/uat_screenshots/live_particle_lab_cannon_flamethrower.png"
        await page.screenshot(path=cannon_shot, full_page=True)
        print(f"📸 Captured Cannon Flamethrower screenshot: {cannon_shot}")
        
        # 2. Click DNA Helix Quick Chip to test Generative HoloDex
        print("🧬 Clicking DNA Helix HoloDex prompt...")
        dna_btn = page.locator("button:has-text('DNA Helix')").first
        await dna_btn.click()
        await asyncio.sleep(2.5)
        
        dna_shot = "/home/james/sovereign_inbox/today/uat_screenshots/live_particle_lab_holodex_dna.png"
        await page.screenshot(path=dna_shot, full_page=True)
        print(f"📸 Captured HoloDex DNA Helix screenshot: {dna_shot}")
        
        # 3. Click Spiral Galaxy Quick Chip
        print("🌌 Clicking Galaxy HoloDex prompt...")
        galaxy_btn = page.locator("button:has-text('Galaxy')").first
        await galaxy_btn.click()
        await asyncio.sleep(2.5)
        
        galaxy_shot = "/home/james/sovereign_inbox/today/uat_screenshots/live_particle_lab_holodex_galaxy.png"
        await page.screenshot(path=galaxy_shot, full_page=True)
        print(f"📸 Captured HoloDex Galaxy screenshot: {galaxy_shot}")
        
        # Copy screenshots to brain artifact directory
        brain_dir = "/home/james/.gemini/antigravity/brain/e3c45a14-6b29-4c1c-9da0-e0344fd40bc8"
        os.system(f"cp {cannon_shot} {brain_dir}/")
        os.system(f"cp {dna_shot} {brain_dir}/")
        os.system(f"cp {galaxy_shot} {brain_dir}/")
        
        print("🔍 Console Logs:")
        for log in console_logs[-10:]:
            print(f"  {log}")
            
        await browser.close()
        print("🏁 UAT Verification Run Complete!")

if __name__ == "__main__":
    asyncio.run(run_uat())
