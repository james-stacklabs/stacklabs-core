import asyncio
import os
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:1934"
ROUTES = [
    {"path": "/?room=starter", "name": "Command Center"},
    {"path": "/?room=snackbar", "name": "Live Chat - Dive Bar"},
    {"path": "/?room=uhf_studio", "name": "Producers Desk & 5-Point Matrix"},
    {"path": "/?room=god_mode", "name": "JSON Injector"},
    {"path": "/?room=persona_console", "name": "Persona Matrix - DB Sync"},
    {"path": "/?room=auditor", "name": "Umpires Review"}
]
SCREENSHOT_DIR = "/home/james/stacklabs/uat_screenshots/ui_manual/"
MANUAL_PATH = "/home/james/stacklabs/dna/agents/SOVEREIGN_ORACLE/payloads/FANSTACK_UI_MASTER_MANUAL.md.txt"

async def main():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MANUAL_PATH), exist_ok=True)
    
    manual_content = [
        "# FanStack UI Master Manual",
        "A complete mapping of all interactive elements across the 01_Sovereign_Portal ecosystem.",
        "Generated dynamically via Headless DOM Crawl.",
        "---"
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        for route in ROUTES:
            print(f"Crawling {route['name']} at {BASE_URL}{route['path']}")
            try:
                # Wait until commit (page starts rendering) so we don't hang if websocket causes page activity to never "idle"
                await page.goto(f"{BASE_URL}{route['path']}", wait_until="commit", timeout=15000)
            except Exception as e:
                print(f"Warning: Navigation error or timeout for {route['name']}: {e}")
            
            # Critical Override: 7 seconds for hydration and websocket
            print("WAITING 7 SECONDS FOR WEBSOCKET HYDRATION...")
            await asyncio.sleep(7)
            
            safe_name = route['name'].replace(' ', '_').replace('/', '').replace('-', '_')
            screenshot_path = os.path.join(SCREENSHOT_DIR, f"{safe_name}.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Saved screenshot: {screenshot_path}")
            
            elements_data = await page.evaluate('''() => {
                const results = { buttons: [], inputs: [], selects: [], sliders: [] };
                
                document.querySelectorAll('button').forEach(el => {
                    const txt = el.innerText.trim() || el.value || el.name || el.id;
                    if (txt && !results.buttons.includes(txt)) results.buttons.push(txt);
                });
                
                document.querySelectorAll('input:not([type="range"])').forEach(el => {
                    const label = el.closest('label')?.innerText.trim() || el.placeholder || el.name || el.id || el.type;
                    if (label && !results.inputs.includes(label)) results.inputs.push(label);
                });
                
                document.querySelectorAll('select').forEach(el => {
                    const label = el.closest('label')?.innerText.trim() || el.name || el.id;
                    if (label && !results.selects.includes(label)) results.selects.push(label);
                });
                
                document.querySelectorAll('input[type="range"]').forEach(el => {
                    const label = el.closest('label')?.innerText.trim() || el.name || el.id;
                    if (label && !results.sliders.includes(label)) results.sliders.push(label);
                });
                
                return results;
            }''')
            
            manual_content.append(f"\n## {route['name']}")
            manual_content.append(f"**Route:** `{route['path']}`\n")
            manual_content.append(f"**Screenshot Vaulted:** `{screenshot_path}`\n")
            manual_content.append("### Interactive Surface Area:")
            
            if elements_data['buttons']:
                manual_content.append("- **Buttons/Triggers:** " + ", ".join(elements_data['buttons']))
            if elements_data['inputs']:
                manual_content.append("- **Input Fields:** " + ", ".join(elements_data['inputs']))
            if elements_data['selects']:
                manual_content.append("- **Dropdowns:** " + ", ".join(elements_data['selects']))
            if elements_data['sliders']:
                manual_content.append("- **Sliders (Dials):** " + ", ".join(elements_data['sliders']))
                
            manual_content.append("---")
            
        await browser.close()
        
    with open(MANUAL_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(manual_content))
    print(f"\n[ORACLE HANDOFF] Master Manual Generated at: {MANUAL_PATH}")

if __name__ == "__main__":
    asyncio.run(main())
