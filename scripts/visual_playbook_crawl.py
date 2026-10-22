#!/usr/bin/env python3
import asyncio
import os
import sys
import json
import shutil
import subprocess
from urllib.parse import urlparse
from playwright.async_api import async_playwright

SOVEREIGN_HOME = "/home/james/stacklabs"
VAULT_DIR = f"{SOVEREIGN_HOME}/vault_matrix"
ASSETS_DIR = f"{VAULT_DIR}/playbook_assets"
PLAYBOOK_PATH = f"{VAULT_DIR}/VISUAL_PLAYBOOK.md"
SESSION_STATE_PATH = f"{SOVEREIGN_HOME}/config/clio_session_state.json"
AUTH_USER = "james"
AUTH_PASS = "!!Stella1977"

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SESSION_STATE_PATH), exist_ok=True)

# List of components, selectors, routes, ports, and file mappings
COMPONENTS = [
    {
        "id": "Cinema_Portal_Container",
        "port": 3008,
        "route": "/",
        "selector": ".cinema-portal-container",
        "file": "02_Sovereign_Media/src/components/CinemaPortal.tsx",
        "desc": "Main Cinema portal frame containing stream grid"
    },
    {
        "id": "Cinema_Hero_Banner",
        "port": 3008,
        "route": "/",
        "selector": ".hero-banner",
        "file": "02_Sovereign_Media/src/components/HeroBanner.tsx",
        "desc": "Cinema main high-light hero banner"
    },
    {
        "id": "Creator_Orchestration_Deck",
        "port": 3009,
        "route": "/",
        "selector": ".orchestration-deck",
        "file": "15_FanStackCreator/src/components/OrchestrationDeck.tsx",
        "desc": "Orchestrator control deck for chatbot settings"
    },
    {
        "id": "Creator_Room_Selector",
        "port": 3009,
        "route": "/",
        "selector": ".room-selector-panel",
        "file": "15_FanStackCreator/src/components/RoomSelectorPanel.tsx",
        "desc": "Room selection panel for active channels"
    },
    {
        "id": "FanStack_LeftNav",
        "port": 3010,
        "route": "/fan-portal?game_room=824910",
        "selector": '[data-section="1"]',
        "file": "19_FanStackArena/src/components/LeftNav.tsx",
        "desc": "Main Left navigation panel for fan hub"
    },
    {
        "id": "FanStack_RoomHeader",
        "port": 3010,
        "route": "/fan-portal?game_room=824910",
        "selector": '[data-section="2"]',
        "file": "19_FanStackArena/src/components/RoomHeader.tsx",
        "desc": "Matchup status and room header panel"
    },
    {
        "id": "FanStack_PlayCallDesk",
        "port": 3010,
        "route": "/fan-portal?game_room=824910",
        "selector": '[data-section="3"]',
        "file": "19_FanStackArena/src/components/PlayCallDesk.tsx",
        "desc": "Live play matchup focus and scorecard desk"
    },
    {
        "id": "FanStack_ChatReactor",
        "port": 3010,
        "route": "/fan-portal?game_room=824910",
        "selector": '[data-section="7"]',
        "file": "19_FanStackArena/src/components/ChatReactor.tsx",
        "desc": "Live websocket chat reactor feed"
    },
    {
        "id": "FanStack_MediaVault",
        "port": 3010,
        "route": "/fan-portal?game_room=824910",
        "selector": ".media-vault-view",
        "click_targets": ["select:#mode-select-dropdown->Media Vault"],
        "file": "19_FanStackArena/src/components/SovereignSportsDashboard.tsx",
        "desc": "Decorum Media Vault UAT Sandbox grid showcasing 17 situational flow video, canvas, and HUD alert assets"
    },
    {
        "id": "AetherVet_ClinicalChart",
        "port": 3015,
        "route": "/",
        "selector": ".clinical-chart-panel",
        "file": "20_AetherVet/src/components/ClinicalChartPanel.tsx",
        "desc": "Clinical chart summary details"
    },
    {
        "id": "AetherVet_Diagnostics",
        "port": 3015,
        "route": "/",
        "selector": "#vet-diagnostics",
        "file": "20_AetherVet/src/components/Diagnostics.tsx",
        "desc": "Diagnostics panel for active tests"
    },
    {
        "id": "GardenStack_LogBoard",
        "port": 3021,
        "route": "/",
        "selector": ".environmental-log-board",
        "file": "21_Wildseed_GardenStack/src/components/EnvironmentalLogBoard.tsx",
        "desc": "Log output for greenhouse sensors"
    },
    {
        "id": "GardenStack_ClimateControls",
        "port": 3021,
        "route": "/",
        "selector": ".greenhouse-climate-controls",
        "file": "21_Wildseed_GardenStack/src/components/GreenhouseClimateControls.tsx",
        "desc": "Climate manipulation controller widget"
    },
    {
        "id": "Storybook_ComponentCanvas",
        "port": 3017,
        "route": "/",
        "selector": ".component-canvas",
        "file": "23_EileenStack/src/components/ComponentCanvas.tsx",
        "desc": "Storybook sandbox canvas viewport"
    },
    {
        "id": "Portal_CommandCenter",
        "port": 3016,
        "route": "/?room=cockpit",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/InteractiveCockpit.tsx",
        "desc": "Main operator control cockpit and navigation center"
    },
    {
        "id": "Portal_PowerTools",
        "port": 3016,
        "route": "/?room=power_tools",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/PowerToolsGrid.tsx",
        "desc": "Grid system for developer tools and diagnostic commands"
    },
    {
        "id": "Portal_KnowledgeHub",
        "port": 3016,
        "route": "/?room=knowledge_hub",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/KnowledgeHub.tsx",
        "desc": "Active Knowledge Base articles and search interface"
    },
    {
        "id": "Portal_Kanban",
        "port": 3016,
        "route": "/?room=kanban",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/LivingKanbanBoard.tsx",
        "desc": "Kanban board for managing active ticket sprints"
    },
    {
        "id": "Portal_PixelDropzone",
        "port": 3016,
        "route": "/?room=pixel_dropzone",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/PixelDropZone.tsx",
        "desc": "Collapsible pixel staging area and file drop drawer"
    },
    {
        "id": "Portal_SovereignStudio",
        "port": 3016,
        "route": "/?room=data",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/SovereignStudio.tsx",
        "desc": "Studio data interface and room visualizer"
    },
    {
        "id": "Portal_MetsyScrapbook",
        "port": 3016,
        "route": "/?room=metsy_adventures",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/MetsyAdventuresWorkspace.tsx",
        "desc": "Adventure generation log and screenshot scrapbook"
    },
    {
        "id": "Portal_PromptInterceptor",
        "port": 3016,
        "route": "/?room=prompt_preview",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/PromptPreviewConsole.tsx",
        "desc": "Prompt preview and raw JSON interception debugger"
    },
    {
        "id": "Portal_CMDB",
        "port": 3016,
        "route": "/?room=cmdb",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/SovereignCmdb.tsx",
        "desc": "Configuration Management Database console"
    },
    {
        "id": "Portal_SovereignCSS",
        "port": 3016,
        "route": "/?room=sovereign_css",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/SovereignCssConsole.tsx",
        "desc": "Direct CSS overrides and styling editor"
    },
    {
        "id": "Portal_SystemRules",
        "port": 3016,
        "route": "/?room=sys_rules",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/SystemRulesConsole.tsx",
        "desc": "Centralized system guidelines and rules lookup"
    },
    {
        "id": "Portal_SystemDocs",
        "port": 3016,
        "route": "/?room=sys_docs",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/SystemDocsHub.tsx",
        "desc": "Archived internal documentation and specs"
    },
    {
        "id": "Portal_OracleGuardrails",
        "port": 3016,
        "route": "/?room=oracle_guardrails",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/OracleGuardrailsConsole.tsx",
        "desc": "Oracle safety guardrails and boundary logs"
    },
    {
        "id": "Portal_FleetTelemetry",
        "port": 3016,
        "route": "/?room=nexus_telemetry",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/NexusTelemetryConsole.tsx",
        "desc": "WebRTC and background network fleet telemetry status"
    },
    {
        "id": "Portal_SystemConfig_Hub",
        "port": 3016,
        "route": "/?room=system_config",
        "selector": ".sovereign-shell-container",
        "file": "01_Sovereign_Portal/src/components/SystemConfigHub.tsx",
        "desc": "Main System Config Hub card layout"
    },
    {
        "id": "Portal_ThemeManager_Slate",
        "port": 3016,
        "route": "/?room=theme_manager",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=Slate Grid"],
        "file": "01_Sovereign_Portal/src/components/SovereignThemeLab.tsx",
        "desc": "Theme Manager: ServiceNow Slate Grid layout"
    },
    {
        "id": "Portal_ThemeManager_CLI",
        "port": 3016,
        "route": "/?room=theme_manager",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=Operator Shell"],
        "file": "01_Sovereign_Portal/src/components/SovereignThemeLab.tsx",
        "desc": "Theme Manager: CLI Operator Shell layout"
    },
    {
        "id": "Portal_ThemeManager_Portfolio",
        "port": 3016,
        "route": "/?room=theme_manager",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=Collapsible Catalog"],
        "file": "01_Sovereign_Portal/src/components/SovereignThemeLab.tsx",
        "desc": "Theme Manager: Collapsible Catalog layout"
    },
    {
        "id": "Portal_UserManagement_Users",
        "port": 3016,
        "route": "/?room=user_management",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=Users"],
        "file": "01_Sovereign_Portal/src/components/UserManagementConsole.tsx",
        "desc": "User Management: Operators List view"
    },
    {
        "id": "Portal_UserManagement_NewUser",
        "port": 3016,
        "route": "/?room=user_management",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=Create Account"],
        "file": "01_Sovereign_Portal/src/components/UserManagementConsole.tsx",
        "desc": "User Management: Create Account profile form"
    },
    {
        "id": "Portal_UserManagement_RBAC",
        "port": 3016,
        "route": "/?room=user_management",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=Access Control"],
        "file": "01_Sovereign_Portal/src/components/UserManagementConsole.tsx",
        "desc": "User Management: Access Control permissions layout"
    },
    {
        "id": "Portal_UserManagement_Profile_WorkOrders",
        "port": 3016,
        "route": "/?room=user_management",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=@james", "text=Assigned Work Orders"],
        "file": "01_Sovereign_Portal/src/components/UserManagementConsole.tsx",
        "desc": "User Profile Detail - james: Assigned Work Orders"
    },
    {
        "id": "Portal_UserManagement_Profile_Achievements",
        "port": 3016,
        "route": "/?room=user_management",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=@james", "text=Achievements & Rewards"],
        "file": "01_Sovereign_Portal/src/components/UserManagementConsole.tsx",
        "desc": "User Profile Detail - james: Achievements & Rewards"
    },
    {
        "id": "Portal_UserManagement_Profile_Lore",
        "port": 3016,
        "route": "/?room=user_management",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=@james", "text=Biography & Deep Lore"],
        "file": "01_Sovereign_Portal/src/components/UserManagementConsole.tsx",
        "desc": "User Profile Detail - james: Biography & Deep Lore"
    },
    {
        "id": "Portal_UserManagement_Profile_Credentials",
        "port": 3016,
        "route": "/?room=user_management",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=@james", "text=Security Credentials"],
        "file": "01_Sovereign_Portal/src/components/UserManagementConsole.tsx",
        "desc": "User Profile Detail - james: Security Credentials"
    },
    {
        "id": "Portal_OpticalIngest_Coprocessor",
        "port": 3016,
        "route": "/?room=optical_ingest",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=HAILO AI ACCELERATOR"],
        "file": "01_Sovereign_Portal/src/components/OpticalIngestConsole.tsx",
        "desc": "Optical Ingest: Hailo AI Coprocessor Dashboard"
    },
    {
        "id": "Portal_OpticalIngest_DVR",
        "port": 3016,
        "route": "/?room=optical_ingest",
        "selector": ".sovereign-shell-container",
        "click_targets": ["text=DIRECT WEBCAM DVR"],
        "file": "01_Sovereign_Portal/src/components/OpticalIngestConsole.tsx",
        "desc": "Optical Ingest: Direct Webcam DVR Stream"
    },
    {
        "id": "FanStack_GamedayScoreboard",
        "port": 3009,
        "route": "/?domain=MLB&room=starter&gamePk=745802",
        "selector": ".gameday-scoreboard-card",
        "file": "15_FanStackCreator/src/components/GamedayScoreboard.tsx",
        "desc": "Prominent high-fidelity glassmorphic scoreboard displaying real-time box score state, counts, outs, and integrated base-runner paths"
    }
]

async def authenticate(context):
    print("[*] Performing authentication session setup...")
    page = await context.new_page()
    try:
        # Check port 8090 auth login first programmatically
        import urllib.request
        url = "http://clio.taila01894.ts.net:8090/api/auth/login"
        data = json.dumps({"username": AUTH_USER, "password": AUTH_PASS}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        token = ""
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            token = res_data.get("token") or ""
            
        await page.goto("https://clio.taila01894.ts.net:3016/", wait_until="networkidle", timeout=10000)
        
        eval_js = f"""
            localStorage.setItem('sov_auth', 'unlocked');
            localStorage.setItem('auth_token', 'sovereign_admin');
            localStorage.setItem('sovereign_user', 'james');
            localStorage.setItem('sovereign_role', 'admin');
            localStorage.setItem('sovereign_spotlight_last_seen_date', new Date().toISOString());
            if ('{token}') {{
                localStorage.setItem('sovereign_session_token', '{token}');
            }}
        """
        await page.evaluate(eval_js)
        await page.reload(wait_until="networkidle", timeout=10000)
        
        # Check for visible login fields
        u = await page.query_selector("input[type='text'], #auth-username, #username")
        p = await page.query_selector("input[type='password'], #auth-password")
        if u and p:
            await u.fill(AUTH_USER)
            await p.fill(AUTH_PASS)
            btn = await page.query_selector("button[type='submit'], #auth-submit")
            if btn:
                await btn.click()
                await page.wait_for_timeout(3000)
                
        # Save state
        await context.storage_state(path=SESSION_STATE_PATH)
        print("[+] Session state saved successfully.")
    except Exception as e:
        print(f"[!] Authentication warning/error: {e}")
    finally:
        await page.close()

async def main():
    print("[*] Running Playwright Visual Playbook Crawler...")
    import platform
    is_argo = platform.machine() == "aarch64"
    
    launch_kwargs = {
        "headless": True,
        "args": ["--ignore-certificate-errors", "--disable-web-security", "--no-sandbox"]
    }
    if is_argo:
        print("[*] Environment-aware launch: target native Chromium on Argo (aarch64)")
        launch_kwargs["executable_path"] = "/usr/bin/chromium"
        launch_kwargs["args"].append("--disable-setuid-sandbox")
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        
        # Use high-density scale factor = 2
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            ignore_https_errors=True
        )
        
        await authenticate(context)
        
        crawled_results = []
        
        for comp in COMPONENTS:
            comp_id = comp["id"]
            port = comp["port"]
            route = comp["route"]
            selector = comp["selector"]
            relative_file = comp["file"]
            desc = comp["desc"]
            
            # Formulate URL
            url = f"https://clio.taila01894.ts.net:{port}{route}"
            print(f"[*] Crawling {comp_id} on Port {port} -> Selector: {selector}...")
            
            page = await context.new_page()
            screenshot_rel_path = f"playbook_assets/{comp_id}.png"
            screenshot_abs_path = f"{ASSETS_DIR}/{comp_id}.png"
            
            status = "MISSING"
            try:
                # Load page
                await page.goto(url, wait_until="networkidle", timeout=10000)
                await page.wait_for_timeout(2000)
                
                # Perform click targets if defined
                click_targets = comp.get("click_targets", [])
                for target in click_targets:
                    if target.startswith("select:"):
                        parts = target[7:].split("->")
                        select_sel = parts[0]
                        option_val = parts[1]
                        print(f"  [*] Selecting option in {select_sel} to: {option_val}")
                        await page.select_option(select_sel, option_val)
                    else:
                        print(f"  [*] Clicking target: {target}")
                        locator = page.locator(target).first
                        await locator.wait_for(state="visible", timeout=5000)
                        await locator.click()
                    await page.wait_for_timeout(1000)
                
                # Check selector existence
                element = None
                selectors_to_try = [selector, "body", "#root"]
                for sel in selectors_to_try:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        element = el
                        if sel != selector:
                            print(f"  [!] Selector {selector} not found. Falling back to {sel}.")
                        break
                        
                if element:
                    await element.scroll_into_view_if_needed()
                    await element.screenshot(path=screenshot_abs_path)
                    print(f"  [+] Saved screenshot slice: {screenshot_rel_path}")
                    status = "OK" if selector in selectors_to_try[:1] else "FALLBACK"
                else:
                    print(f"  [!] No valid selectors found on page.")
                    status = "MISSING"
            except Exception as ex:
                print(f"  [!] Exception crawling {comp_id}: {ex}")
                status = "ERROR"
            finally:
                await page.close()
                
            crawled_results.append({
                "id": comp_id,
                "status": status,
                "port": port,
                "route": route,
                "selector": selector,
                "file": f"{SOVEREIGN_HOME}/{relative_file}",
                "screenshot": screenshot_rel_path,
                "desc": desc
            })
            
        await browser.close()
        
    # Compile markdown playbook
    print("[*] Compiling VISUAL_PLAYBOOK.md index...")
    import socket
    hostname = socket.gethostname()
    md_content = f"""# Sovereign OS — Visual Playbook Index
**Generated:** Programmatic Playwright Crawler Sweep
**Node Host:** {hostname}

---

## 🎨 Visual Component Catalog

"""
    for res in crawled_results:
        md_content += f"""### Card ID: `{res['id']}`
* **Status:** `{res['status']}`
* **Ecosystem Port:** `{res['port']}`
* **Target Route:** `{res['route']}`
* **HTML Selector:** `{res['selector']}`
* **React Source Component:** [{os.path.basename(res['file'])}](file://{res['file']})
* **Description:** {res['desc']}

![{res['id']}]({res['screenshot']})

---

"""
        
    with open(PLAYBOOK_PATH, "w") as f:
        f.write(md_content)
    print(f"[+] Written playbook index to: {PLAYBOOK_PATH}")
    
    # Sync to Google Drive
    print("[*] Detecting available rclone remote...")
    remotes_res = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True)
    available_remotes = [r.strip().replace(":", "") for r in remotes_res.stdout.splitlines() if r.strip()]
    
    target_remote = "sovereign_clio_sync"
    if "sovereign_clio_sync" not in available_remotes:
        if "sovereign_os" in available_remotes:
            target_remote = "sovereign_os"
        elif "gdrive" in available_remotes:
            target_remote = "gdrive"
        elif available_remotes:
            target_remote = available_remotes[0]
            
    print(f"[*] Synchronizing Playbook folder to Google Drive using remote: {target_remote}...")
    sync_cmd = [
        "rclone", "copy",
        VAULT_DIR,
        f"{target_remote}:Sovereign OS Visual Playbook/"
    ]
    sync_res = subprocess.run(sync_cmd, capture_output=True, text=True)
    if sync_res.returncode == 0:
        print("[+] Playbook synchronization completed successfully.")
    else:
        print(f"[!] Sync failed: {sync_res.stderr}")

if __name__ == "__main__":
    asyncio.run(main())
