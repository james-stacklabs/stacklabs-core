#!/usr/bin/env python3
"""
Sovereign OS: FanStack Creator Portal (Port 3009) Autonomous Playwright Crawler & Visual Auditor
Path: /home/james/stacklabs/scripts/crawl_fanstack_portal_3009.py
Ticket: WO-2026-0910-FANSTACK-PORTAL-CRAWL-LOOKBOOK
"""

import os
import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "https://clio.taila01894.ts.net:3009"
OUTPUT_DIR = Path("/home/james/sovereign_inbox/reports/portal_3009_lookbook_assets")
TICKET_UAT_DIR = Path("/home/james/sovereign_inbox/tickets/WO-2026-0910-FANSTACK-PORTAL-CRAWL-LOOKBOOK/uat")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TICKET_UAT_DIR.mkdir(parents=True, exist_ok=True)

# Define routes to crawl
ROUTES_TO_CRAWL = [
    # Root & Domains
    {"id": "01_portal_home", "name": "FanStack Portal Root", "url": f"{BASE_URL}/?domain=PORTAL", "category": "Core"},
    {"id": "02_domain_mlb_command_center", "name": "MLB Command Center (Starter)", "url": f"{BASE_URL}/?domain=MLB&room=starter", "category": "Live Operations"},
    {"id": "03_domain_nfl", "name": "NFL Crosstalk Lounge", "url": f"{BASE_URL}/?domain=NFL", "category": "Live Operations"},
    {"id": "04_domain_pga", "name": "PGA Amen Corner", "url": f"{BASE_URL}/?domain=PGA", "category": "Live Operations"},

    # Media Pipeline & Synthesis
    {"id": "05_media_holodex", "name": "Sovereign HoloDex", "url": f"{BASE_URL}/?domain=GLOBAL&room=holodex", "category": "Media Pipeline"},
    {"id": "06_media_storyboard", "name": "Storyboard Deck", "url": f"{BASE_URL}/?domain=GLOBAL&room=storyboard_deck", "category": "Media Pipeline"},
    {"id": "07_media_watch_party", "name": "Sovereign Watch Party", "url": f"{BASE_URL}/?domain=GLOBAL&room=rom_gallery", "category": "Media Pipeline"},
    {"id": "08_media_highlight_heist", "name": "Highlight Heist", "url": f"{BASE_URL}/?domain=GLOBAL&room=highlight_heist", "category": "Media Pipeline"},
    {"id": "09_media_stream_sniper", "name": "Stream Sniper", "url": f"{BASE_URL}/?domain=GLOBAL&room=stream_sniper", "category": "Media Pipeline"},
    {"id": "10_media_tmi_news_desk", "name": "TMI News Desk", "url": f"{BASE_URL}/?domain=GLOBAL&room=tmi_news_desk", "category": "Media Pipeline"},
    {"id": "11_media_mam_tmi_console", "name": "MAM & TMI Console", "url": f"{BASE_URL}/?domain=GLOBAL&room=mam_tmi_console", "category": "Media Pipeline"},

    # Intelligence & Core Infrastructure
    {"id": "12_intel_pile_dvr", "name": "Pile DVR (Webcam Capture)", "url": f"{BASE_URL}/?domain=GLOBAL&room=optical_ingest", "category": "Intelligence & Core"},
    {"id": "13_intel_persona_command", "name": "Persona Command Center", "url": f"{BASE_URL}/?domain=GLOBAL&room=persona_console", "category": "Intelligence & Core"},
    {"id": "14_intel_advocate_center", "name": "Advocate Center & Lookbook", "url": f"{BASE_URL}/?domain=GLOBAL&room=advocate_center", "category": "Intelligence & Core"},
    {"id": "15_intel_advocate_lookbook", "name": "Advocate Lookbook Print Deck", "url": f"{BASE_URL}/?domain=GLOBAL&room=advocate_lookbook", "category": "Intelligence & Core"},
    {"id": "16_intel_clio_cockpit", "name": "Clio Cockpit Dashboard", "url": f"{BASE_URL}/?domain=GLOBAL&room=cockpit", "category": "Intelligence & Core"},
    {"id": "17_intel_savant_oracle", "name": "Savant Oracle Analytics", "url": f"{BASE_URL}/?domain=GLOBAL&room=savant_query", "category": "Intelligence & Core"},
    {"id": "18_intel_daily_roll_call", "name": "Daily Roll Call", "url": f"{BASE_URL}/?domain=GLOBAL&room=roll_call", "category": "Intelligence & Core"},
    {"id": "19_intel_room_builder", "name": "Room Builder & Config", "url": f"{BASE_URL}/?domain=GLOBAL&room=room_builder", "category": "Intelligence & Core"},
    {"id": "20_intel_media_vault_matrix", "name": "Media Vault Matrix", "url": f"{BASE_URL}/?domain=GLOBAL&room=artifact_gallery", "category": "Intelligence & Core"},
    {"id": "21_intel_token_ledger", "name": "Token Ledger & ROI", "url": f"{BASE_URL}/?domain=GLOBAL&room=token_ledger", "category": "Intelligence & Core"},

    # Umpire & Prediction / Simulation
    {"id": "22_umpire_review", "name": "Umpire's Review", "url": f"{BASE_URL}/?domain=GLOBAL&room=auditor", "category": "Umpire & Prediction"},
    {"id": "23_card_simulator", "name": "Card Simulator & Physics", "url": f"{BASE_URL}/?domain=GLOBAL&room=card_simulator", "category": "Umpire & Prediction"},

    # Live Operations
    {"id": "24_live_playcall_desk", "name": "Playcall Desk Consolidated", "url": f"{BASE_URL}/?domain=GLOBAL&room=playcall_desk", "category": "Live Operations"},
    {"id": "25_live_the_skew", "name": "The Skew (Live)", "url": f"{BASE_URL}/?domain=GLOBAL&room=the_skew", "category": "Live Operations"},
    {"id": "26_live_hot_takes", "name": "Hot Takes Rant Matrix", "url": f"{BASE_URL}/?domain=GLOBAL&room=hot_takes", "category": "Live Operations"},
    {"id": "27_live_chat_sniper", "name": "Live Chat Sniper", "url": f"{BASE_URL}/?domain=GLOBAL&room=live_chat_sniper", "category": "Live Operations"},
    {"id": "28_live_cosmic_sieve", "name": "The Cosmic Sieve (Promo Inbox)", "url": f"{BASE_URL}/?domain=GLOBAL&room=promo_inbox", "category": "Live Operations"},
    {"id": "29_live_game_log_export", "name": "Game Log Export", "url": f"{BASE_URL}/?domain=GLOBAL&room=game_log_export", "category": "Live Operations"},
]

def run_crawl():
    print(f"[*] Starting FanStack Portal 3009 Playwright Discovery Crawl...")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        
        # Inject auth bypass and theme preference into every page
        context.add_init_script("""
            localStorage.setItem('sov_auth', 'unlocked');
            localStorage.setItem('sovereign_theme', 'sovereign-home');
        """)

        page = context.new_page()

        # Step 1: Visit Portal Root to unlock and verify
        print(f"[➔] Testing root access and extranet bypass...")
        try:
            page.goto(f"{BASE_URL}/?domain=PORTAL&vip=creator", wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(2000)
            # If extranet unlock code input is present, submit WARDYNYM
            if page.locator("input[type='password']").count() > 0:
                print("  [!] Extranet access gate detected. Injecting WARDYNYM unlock...")
                page.fill("input[type='password']", "WARDYNYM")
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)
        except Exception as e:
            print(f"  [!] Warning on initial unlock: {e}")

        # Step 2: Iterate through all defined routes
        for item in ROUTES_TO_CRAWL:
            route_id = item["id"]
            name = item["name"]
            url = item["url"]
            category = item["category"]

            print(f"[➔] Crawling [{category}] {name} -> {url}")
            t0 = time.time()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=12000)
                page.wait_for_timeout(2500)  # Allow React rendering & state hooks

                # File paths
                screenshot_filename = f"{route_id}.png"
                out_path = OUTPUT_DIR / screenshot_filename
                ticket_path = TICKET_UAT_DIR / screenshot_filename

                page.screenshot(path=str(out_path), full_page=False)
                # Copy to ticket uat dir as well
                page.screenshot(path=str(ticket_path), full_page=False)

                duration = round(time.time() - t0, 2)
                title = page.title()
                results.append({
                    "id": route_id,
                    "name": name,
                    "category": category,
                    "url": url,
                    "screenshot": screenshot_filename,
                    "duration_sec": duration,
                    "status": "SUCCESS",
                    "page_title": title
                })
                print(f"  [✔] Captured {screenshot_filename} in {duration}s")
            except Exception as err:
                print(f"  [❌] Error capturing {name}: {err}")
                results.append({
                    "id": route_id,
                    "name": name,
                    "category": category,
                    "url": url,
                    "screenshot": None,
                    "duration_sec": round(time.time() - t0, 2),
                    "status": f"FAILED: {str(err)}",
                    "page_title": None
                })

        # Step 3: Deep Dive on Command Center Games Slate
        print("\n[*] Executing Deep Dive Analysis on Command Center Daily Games Slate...")
        try:
            page.goto(f"{BASE_URL}/?domain=MLB&room=starter", wait_until="domcontentloaded", timeout=12000)
            page.wait_for_timeout(3000)

            # Isolate the slate bar
            slate_locator = page.locator("div:has(> div > h1:has-text('MLB'))").first
            slate_screenshot = OUTPUT_DIR / "deep_dive_command_center_slate.png"
            slate_ticket = TICKET_UAT_DIR / "deep_dive_command_center_slate.png"

            if slate_locator.count() > 0:
                slate_locator.screenshot(path=str(slate_screenshot))
                slate_locator.screenshot(path=str(slate_ticket))
                print("  [✔] Isolated slate component screenshot captured!")
            else:
                print("  [!] Specific selector not found, capturing top area viewport...")
                page.screenshot(path=str(slate_screenshot), clip={"x": 0, "y": 0, "width": 1920, "height": 300})
                page.screenshot(path=str(slate_ticket), clip={"x": 0, "y": 0, "width": 1920, "height": 300})

            # Inspect DOM & React Fiber details
            dom_analysis = page.evaluate("""() => {
                const slate = document.querySelector("div[class*='backdrop-blur-xl']");
                const mlbHeader = Array.from(document.querySelectorAll('h1, span')).find(el => el.textContent.trim() === 'MLB');
                const games = Array.from(document.querySelectorAll("div[class*='cursor-pointer']")).filter(el => el.textContent.includes('@'));
                
                return {
                    hasSlateElement: !!slate,
                    headerText: mlbHeader ? mlbHeader.textContent : null,
                    renderedGamesCount: games.length,
                    renderedGameSamples: games.slice(0, 3).map(g => g.innerText.replace(/\\n+/g, ' | ')),
                    parentContainerClass: slate ? slate.parentElement?.className : null
                };
            }""")
            print(f"  [✔] DOM Analysis: {json.dumps(dom_analysis, indent=2)}")

        except Exception as e:
            print(f"  [❌] Deep dive error: {e}")
            dom_analysis = {"error": str(e)}

        browser.close()

    # Save manifest
    manifest_path = OUTPUT_DIR / "crawl_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump({"timestamp": time.time(), "routes": results, "slate_analysis": dom_analysis}, f, indent=2)
    print(f"\n[✔] Discovery crawl completed! Manifest saved to {manifest_path}")

if __name__ == "__main__":
    run_crawl()
