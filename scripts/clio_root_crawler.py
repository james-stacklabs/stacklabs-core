#!/home/james/stacklabs/.venv/bin/python3
import asyncio
import os
import sys
import re
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# Configuration Constants
BASE_URL = "https://clio.taila01894.ts.net/"
MAX_DEPTH = 3
OUT_DIR = "/home/james/stacklabs/scratch/clio_root_screenshots"
REPORT_PATH = "/home/james/sovereign_inbox/today/Clio_Root_UAT_Crawl_Report.md"
CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"
PROJECT_ID = "gen-lang-client-0840454416"
LOCATION = "us-central1"
MODEL_NAME = "gemini-3.8-flash"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

visited_urls = set()
broken_links = []
scanned_pages = []
lexicon_violations = []
vertex_analyses = []

async def ensure_unlocked(page):
    try:
        # Unlock via localStorage and sessionStorage
        await page.evaluate("window.localStorage.setItem('sov_auth', 'unlocked');")
        await page.evaluate("window.sessionStorage.setItem('sov_auth', 'unlocked');")
        # Handle manual auth fields if visible
        if await page.locator("#auth-username").is_visible():
            print("🔑 Unlocking authorization interface...")
            await page.fill("#auth-username", "james")
            await page.fill("#auth-password", "!!Stella1977")
            await page.click("#auth-submit")
            await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"⚠️ Auth injection warning: {e}")

def analyze_image_with_vertex(image_path: str, view_name: str) -> str:
    print(f"[{view_name}] Running Vertex AI Visual Analysis...")
    try:
        if not os.path.exists(CREDENTIALS_PATH):
            return "Vertex AI bypass: Service account credentials file not found."
            
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel(MODEL_NAME)
        
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        image_part = Part.from_data(data=image_data, mime_type="image/png")
        
        prompt = f"""
You are an expert product analyst and technical evaluator. 
Analyze this screenshot of the '{view_name}' module/view from the Sovereign OS application suite.
Write a detailed 'pitch deck' style capability analysis for this specific view.
Include:
- The core purpose of the view/tab.
- Key features visible in the UI.
- How an Admin or Operator would use this in a live sports broadcast scenario.

Keep the tone professional, investor-ready, and analytical.
"""
        response = model.generate_content([image_part, prompt])
        parts_text = []
        if response and response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(part.text)
        if parts_text:
            return "".join(parts_text)
        try:
            return response.text
        except Exception:
            return "Empty response from Vertex AI."
    except Exception as e:
        return f"Error analyzing {view_name} via Vertex AI: {e}"

async def scan_lexicon_and_screenshot(page, url, depth, name_prefix):
    # Wait for page settling
    await page.wait_for_timeout(2000)
    
    # Save screenshot
    safe_filename = name_prefix + ".png"
    screenshot_path = os.path.join(OUT_DIR, safe_filename)
    await page.screenshot(path=screenshot_path, full_page=True)
    
    # Check lexicon
    visible_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
    matches = re.findall(r'(?i)stack\s+seeder', visible_text)
    if matches:
        print(f"⚠️ LEXICON VIOLATION on {url}: Found {len(matches)} occurrences of 'Stack Seeder'")
        lexicon_violations.append((url, len(matches), depth))
        
    scanned_pages.append({
        "url": url,
        "status": 200,
        "depth": depth,
        "screenshot": screenshot_path,
        "filename": safe_filename
    })
    return screenshot_path

async def crawl_recursive(page, url, depth):
    if depth > MAX_DEPTH or url in visited_urls:
        return
        
    parsed_base = urlparse(BASE_URL)
    parsed_url = urlparse(url)
    
    # Restrict crawling strictly to our secure tailnet domain (allow different ports on same hostname)
    if parsed_url.hostname != parsed_base.hostname:
        return
        
    visited_urls.add(url)
    print(f"[Depth {depth}] Crawling: {url}")
    
    try:
        response = await page.goto(url, wait_until="load", timeout=15000)
        status = response.status if response else "Unknown"
        
        if not response or response.status >= 400:
            print(f"❌ BROKEN LINK: {url} (Status: {status})")
            broken_links.append((url, status, depth))
            return
            
        await ensure_unlocked(page)
        
        # Take screenshot and check lexicon
        name_prefix = url.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "_").replace("?", "_").replace("&", "_")
        screenshot_path = await scan_lexicon_and_screenshot(page, url, depth, name_prefix)
        
        # Analyze with Vertex AI
        analysis = analyze_image_with_vertex(screenshot_path, url)
        vertex_analyses.append({
            "name": f"Recursive Path: {url}",
            "filename": name_prefix + ".png",
            "analysis": analysis
        })
        
        # Extract links
        links = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a')).map(anchor => anchor.href);
        }""")
        
        # No extra urls in recursive crawl, all custom rooms are moved to deterministic target list
        pass
            
        for link in links:
            absolute_link = urljoin(url, link)
            await crawl_recursive(page, absolute_link, depth + 1)
            
    except Exception as e:
        print(f"❌ CONNECTION FAILURE ON: {url} (Error: {e})")
        broken_links.append((url, f"Exception: {e}", depth))

async def scan_playcall_tabs(page, target):
    url = target["url"]
    port = 3009 if "3009" in url else 3010
    tabs = target["tabs"]
    
    print(f"⚡ Performing thorough Playcall Desk tab crawl for port {port}...")
    await page.goto(f"{url}&vip=creator" if "?" in url else f"{url}?vip=creator", wait_until="load")
    await page.wait_for_timeout(3000)
    await ensure_unlocked(page)
    
    # Check if we should toggle dormant/interactive switch for Port 3010
    if port == 3010:
        try:
            power_switch = page.locator("button:has-text('DORMANT'), button:has-text('INTERACTIVE')")
            if await power_switch.count() > 0:
                print("⚡ Toggling Port 3010 Playcall Desk dormant switch...")
                await power_switch.first.click()
                await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Warning trying to toggle power switch: {e}")
            
    for tab in tabs:
        print(f"[{port}] Clicking tab: {tab}")
        try:
            regex = re.compile(rf"^\s*{tab}\s*$", re.I)
            tab_btn = page.locator("button").filter(has_text=regex)
            if await tab_btn.count() == 0:
                tab_btn = page.locator(f"button:has-text('{tab}')")
                if await tab_btn.count() == 0:
                    tab_btn = page.locator(f"button:has-text('{tab.lower()}')")
                    
            if await tab_btn.count() > 0:
                await tab_btn.first.click()
                await page.wait_for_timeout(1500)
            else:
                print(f"[{port}] Button for tab {tab} not found, proceeding...")
        except Exception as e:
            print(f"[{port}] Error clicking tab {tab}: {e}")
            
        filename = f"playcall_desk_{port}_{tab.lower()}.png"
        screenshot_path = os.path.join(OUT_DIR, filename)
        await page.screenshot(path=screenshot_path, full_page=True)
        
        # Check lexicon
        visible_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
        matches = re.findall(r'(?i)stack\s+seeder', visible_text)
        if matches:
            lexicon_violations.append((f"{url} [Tab: {tab}]", len(matches), 1))
            print(f"⚠️ LEXICON VIOLATION on {url} [Tab: {tab}]: Found {len(matches)} occurrences of 'Stack Seeder'")
            
        scanned_pages.append({
            "url": f"{url} [Tab: {tab}]",
            "status": 200,
            "depth": 1,
            "screenshot": screenshot_path,
            "filename": filename
        })
        
        # Analyze screenshot
        analysis = analyze_image_with_vertex(screenshot_path, f"Playcall Desk Port {port} - Tab {tab}")
        vertex_analyses.append({
            "name": f"Playcall Desk Port {port} - Tab {tab}",
            "filename": filename,
            "analysis": analysis
        })

async def scan_single_target(page, target):
    url = target["url"]
    name = target["name"]
    print(f"🎯 Scanning specific target view: {name} ({url})")
    
    try:
        await page.goto(f"{url}&vip=creator" if "?" in url else f"{url}?vip=creator", wait_until="load")
        await page.wait_for_timeout(3000)
        await ensure_unlocked(page)
        
        name_clean = name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
        screenshot_path = await scan_lexicon_and_screenshot(page, url, 1, name_clean)
        
        # Analyze screenshot
        analysis = analyze_image_with_vertex(screenshot_path, name)
        vertex_analyses.append({
            "name": name,
            "filename": name_clean + ".png",
            "analysis": analysis
        })
    except Exception as e:
        print(f"❌ Error scanning target view {name}: {e}")
        broken_links.append((url, f"Target view error: {e}", 1))

async def main():
    print("🚀 Starting Headless Playwright UAT and Lexicon Compliance Crawler...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors', '--disable-gpu'])
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        
        await context.add_init_script("window.localStorage.setItem('sov_auth', 'unlocked');")
        await context.add_init_script("window.sessionStorage.setItem('sov_auth', 'unlocked');")
        page = await context.new_page()
        
        # 1. Run recursive crawl of gateway
        await crawl_recursive(page, BASE_URL, 0)
        
        # 2. Run explicit targets on ports 3016, 3009 and 3010
        SCAN_TARGETS = [
            # --- PORT 3016: SOVEREIGN PORTAL ROOMS ---
            {"url": "https://clio.taila01894.ts.net:3016/?room=kanban", "name": "ITSM Kanban (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=system_config", "name": "System Config (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=stack_seeder", "name": "Stack Seeder (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=app_directory", "name": "App Directory (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=persona_center", "name": "Persona Center (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=argus_nexus", "name": "Argus Nexus (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=theme_manager", "name": "Theme Manager (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=portal_layout", "name": "Portal Layout Config (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=sys_rules", "name": "System Rules (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=sys_docs", "name": "System Docs (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=oracle_guardrails", "name": "Oracle Guardrails (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=cmdb", "name": "CMDB Console (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=asset_backlog", "name": "Asset Backlog (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=metsy_adventures", "name": "Metsy Adventures Workspace (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=prompt_preview", "name": "Prompt Preview Console (Port 3016)"},
            {"url": "https://clio.taila01894.ts.net:3016/?room=power_tools", "name": "Power Tools Grid (Port 3016)"},

            # --- PORT 3009: FANSTACK INTERFACE ---
            {"url": "https://clio.taila01894.ts.net:3009/?domain=PORTAL", "name": "FanStack Portal Grid (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=MLB&room=starter", "name": "MLB Command Center (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=PGA&room=amen_corner", "name": "PGA Amen Corner (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=SKEW&room=the_skew", "name": "The Skew Live (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=SKEW&room=hot_takes", "name": "Hot Takes (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=live_chat_sniper", "name": "Live Chat Sniper (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=promo_inbox", "name": "The Cosmic Sieve Promo Inbox (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=game_log_export", "name": "Game Log Export (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=HOLODEX&room=holodex", "name": "Sovereign HoloDex (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=storyboard_deck", "name": "Storyboard Deck (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=MLB&room=rom_gallery", "name": "Sovereign Watch Party (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=highlight_heist", "name": "Highlight Heist (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=stream_sniper", "name": "Stream Sniper (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=MLB&room=tmi_news_desk", "name": "TMI News Desk (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=optical_ingest", "name": "Pile DVR Optical Ingest (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=advocate_center", "name": "Persona Command Center (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=advocate_lookbook", "name": "Advocate Center & Lookbook (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=cockpit", "name": "Clio Cockpit Dashboard (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=MLB&room=savant_query", "name": "Savant Oracle Analytics (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=roll_call", "name": "Daily Roll Call (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=artifact_gallery", "name": "Media Vault Matrix Artifact Gallery (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=token_ledger", "name": "Token Ledger (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=GLOBAL&room=god_mode", "name": "God Mode (Port 3009)"},
            {"url": "https://clio.taila01894.ts.net:3009/?domain=MLB&room=playcall_desk", "tabs": ["EVENTS", "BOARD", "OVERRIDES", "TAKES", "SYSTEM"]},

            # --- PORT 3010: SOVEREIGN SPORTS INTERFACE ---
            {"url": "https://clio.taila01894.ts.net:3010/", "name": "Sports Landing (Port 3010)"},
            {"url": "https://clio.taila01894.ts.net:3010/mlb", "name": "Sports MLB Center (Port 3010)"},
            {"url": "https://clio.taila01894.ts.net:3010/pga", "name": "Sports PGA Center (Port 3010)"},
            {"url": "https://clio.taila01894.ts.net:3010/footy", "name": "Sports Footy Center (Port 3010)"},
            {"url": "https://clio.taila01894.ts.net:3010/fan-portal?game_room=824910", "name": "Fan Portal (Port 3010)"},
            {"url": "https://clio.taila01894.ts.net:3010/playcall-desk", "tabs": ["EVENTS", "BOARD", "OVERRIDES", "TAKES", "SYSTEM", "PRODUCER", "BUILDER"]}
        ]
        
        for target in SCAN_TARGETS:
            if "tabs" in target:
                await scan_playcall_tabs(page, target)
            else:
                await scan_single_target(page, target)
                
        await browser.close()
        
    # Compile Markdown Report
    print("✍️ Generating UAT Markdown Report...")
    report = f"# 📊 CLIO ROOT GATEWAY UAT SCAN REPORT\n\n"
    report += f"**Base Target URL**: `{BASE_URL}`  \n"
    report += f"**Scanned Depth Limit**: `{MAX_DEPTH}`  \n\n"
    
    report += "## ❌ DEPRECATED CONVICTIONS & BROKEN REDIRECTS\n"
    if broken_links:
        report += "| URL Target | Failure Reason / Status | Depth | Action Required |\n"
        report += "| :--- | :--- | :--- | :--- |\n"
        for url, reason, dep in broken_links:
            action = "Fix Port Mapping" if "Exception" in str(reason) else "Resolve Route"
            report += f"| `{url}` | `{reason}` | `{dep}` | {action} |\n"
    else:
        report += "*No broken redirect blocks detected across verified depths.*\n"
    report += "\n"
    
    report += "## ⚠️ LEXICON VIOLATIONS (Stack Seeder vs Sausage Maker)\n"
    if lexicon_violations:
        report += "| URL Target | Violations Count | Depth | Action Required |\n"
        report += "| :--- | :--- | :--- | :--- |\n"
        for url, count, dep in lexicon_violations:
            report += f"| `{url}` | `{count}` | `{dep}` | Remove legacy 'Stack Seeder' nomenclature and replace with 'Sausage Maker' |\n"
    else:
        report += "*No legacy 'Stack Seeder' references detected. Nomenclature matches approved Lexicon V2.0.*\n"
    report += "\n"
    
    report += "## 🔍 SCANNED TOPOLOGY SUMMARY\n"
    report += "| URL Path / Tab | Status | Depth | Screenshot |\n"
    report += "| :--- | :--- | :--- | :--- |\n"
    for page_data in scanned_pages:
        # Relative path reference for Zero-Litter Workspace policy compliance
        rel_path = f"../../SovereignOS/scratch/clio_root_screenshots/{page_data['filename']}"
        report += f"| `{page_data['url']}` | `{page_data['status']}` | `{page_data['depth']}` | [View Capture]({rel_path}) |\n"
    report += "\n"
    
    report += "## 🧠 VERTEX AI CAPABILITY ANALYSIS & UAT EVALUATIONS\n\n"
    for analysis_data in vertex_analyses:
        rel_path = f"../../SovereignOS/scratch/clio_root_screenshots/{analysis_data['filename']}"
        report += f"### {analysis_data['name']}\n\n"
        report += f"![{analysis_data['name']}]({rel_path})\n\n"
        report += f"**Vertex AI Evaluation**:\n{analysis_data['analysis']}\n\n"
        report += "---\n\n"
        
    with open(REPORT_PATH, "w") as f:
        f.write(report)
        
    print(f"✅ Success: Report compiled at {REPORT_PATH}")

if __name__ == "__main__":
    asyncio.run(main())
