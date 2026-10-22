#!/usr/bin/env python3
"""
Sovereign OS — System-Wide Automated Integrity Crawler & Session Audit
======================================================================
Author: Antigravity & The Pilot (StackLabs LLC)
Date: 2026-06-16

A headless diagnostic tool that programmatically logs into active Sovereign OS
endpoints (Ports 3016, 3020, 3010, 3017), tests session/cookie persistence,
detects auth loop redirects, and scans the DOM for rebranding regressions
(specifically "Persona Center" or "Savant" occurrences instead of "Advocate Center"
or "Sovereign Oracle").

Prerequisite:
    pip install playwright
    playwright install chromium

Usage:
    python3 audit_sovereign_os.py --host clio.taila01894.ts.net --user pawel --pass lfgm2026
"""

import asyncio
import sys
import json
import argparse
from pathlib import Path
from playwright.async_api import async_playwright

async def run_audit(host, username, password):
    print("==============================================================")
    print("🌐 STARTING SOVEREIGN OS SYSTEM-WIDE PLAYWRIGHT CRAWLER AUDIT")
    print("==============================================================")
    
    base_urls = {
        "StackLabs Creator Portal": f"https://{host}:3016",
        "Barb Stack": f"https://{host}:3020",
        "Fan Portal": f"https://{host}:3010",
        "Eileen Stack": f"https://{host}:3017"
    }
    
    audit_report = {
        "status": "COMPLETED",
        "host_target": host,
        "session_persistence_test": "FAILED",
        "auth_redirects_detected": [],
        "rebrand_violations": [],
        "crawled_pages": {}
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Create an isolated browser context
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        
        # -------------------------------------------------------------
        # STEP 1: INITIAL LOGIN & PERSISTENCE TEST
        # -------------------------------------------------------------
        target_portal = base_urls["StackLabs Creator Portal"]
        print(f"\n[STEP 1] Navigating to primary Creator Portal login: {target_portal}")
        try:
            await page.goto(target_portal, timeout=10000)
            await page.wait_for_load_state("networkidle")
            
            # Check if login is required
            if "login" in page.url or await page.query_selector("input[type='password']"):
                print("[AUTH] Login gate detected. Injecting credentials...")
                # Fill in fields - adaptive targeting for standard username/password inputs
                user_input = await page.query_selector("input[type='text'], input[type='email']")
                pass_input = await page.query_selector("input[type='password']")
                
                if user_input and pass_input:
                    await user_input.fill(username)
                    await pass_input.fill(password)
                    submit_btn = await page.query_selector("button[type='submit'], button:has-text('Login'), button:has-text('Sign In'), button:has-text('Dump')")
                    if submit_btn:
                        await submit_btn.click()
                        await page.wait_for_load_state("networkidle")
                        print(f"[AUTH] Login submitted. Directed URL: {page.url}")
            
            # Retrieve and inspect session cookies
            cookies = await context.cookies()
            print(f"[AUTH] Active Session Cookies committed: {[c['name'] for c in cookies]}")
            
            # Check for standard session token or cookie persistence keys
            has_session = any(c['name'] in ['session_id', 'token', 'auth_token', 'session', 'sovereign_session_token'] for c in cookies)
            if has_session:
                audit_report["session_persistence_test"] = "PASSED"
                print("✅ [AUTH PASS] Session cookie verified in storage context.")
            else:
                print("⚠️ [AUTH WARNING] No standard session cookie found in local storage context. Wires may be crossed.")
                
        except Exception as e:
            print(f"❌ [STEP 1 FAILED] Connection timeout or page error on {target_portal}: {e}")
            audit_report["status"] = "INCOMPLETE"
            await browser.close()
            return audit_report

        # -------------------------------------------------------------
        # STEP 2: CRAWLING ENDPOINTS & DETECTING REDIRECT LOOP
        # -------------------------------------------------------------
        print("\n[STEP 2] Crawling stack endpoints to identify login redirection loops...")
        for name, url in base_urls.items():
            print(f"\nChecking [ {name} ] at {url}...")
            try:
                # Direct navigation attempt using active session cookies
                await page.goto(url, timeout=10000)
                await page.wait_for_load_state("domcontentloaded")
                current_url = page.url
                
                # If redirected back to login page, record the loop block
                if "login" in current_url.lower() and "login" not in url.lower():
                    print(f"❌ [AUTH REDIRECT LOOP] Navigating to {url} redirected back to login gate {current_url}")
                    audit_report["auth_redirects_detected"].append({
                        "source_target": name,
                        "intended_url": url,
                        "redirect_destination": current_url
                    })
                else:
                    print(f"✅ [ENDPOINT REACHED] Clean access confirmed for {name}: {current_url}")
                    
                # -------------------------------------------------------------
                # STEP 3: SCANNING DOM FOR REBRAND REGRESSIONS
                # -------------------------------------------------------------
                body_content = await page.content()
                
                # Check for "Persona Center" (case-insensitive)
                persona_matches = len(await page.locator("text=/Persona Center/i").all_inner_texts())
                savant_matches = len(await page.locator("text=/Savant/i").all_inner_texts())
                
                page_results = {
                    "url": current_url,
                    "persona_center_occurrences": persona_matches,
                    "savant_occurrences": savant_matches
                }
                
                audit_report["crawled_pages"][name] = page_results
                
                if persona_matches > 0:
                    msg = f"⚠️ [REBRAND REGRESSION] Found {persona_matches} occurrences of 'Persona Center' on {name} (Should be 'Advocate Center')."
                    print(msg)
                    audit_report["rebrand_violations"].append({
                        "portal": name,
                        "url": current_url,
                        "term_found": "Persona Center",
                        "occurrences": persona_matches
                    })
                    
                if savant_matches > 0:
                    msg = f"⚠️ [REBRAND REGRESSION] Found {savant_matches} occurrences of 'Savant' on {name} (Should be 'Sovereign Oracle')."
                    print(msg)
                    audit_report["rebrand_violations"].append({
                        "portal": name,
                        "url": current_url,
                        "term_found": "Savant",
                        "occurrences": savant_matches
                    })
                    
            except Exception as e:
                print(f"❌ [CRAWL ERROR] Failed to audit {name}: {e}")
                
        await browser.close()
        
    print("\n==============================================================")
    print("🎯 CRAWLER AUDIT COMPLETED. COMPILING RESULTS...")
    print("==============================================================")
    return audit_report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sovereign OS Playwright Integrations Auditor")
    parser.add_argument("--host", default="clio.taila01894.ts.net", help="Tailscale host name or IP")
    parser.add_argument("--user", default="pawel", help="Diagnostic login username")
    parser.add_argument("--pass", dest="password", default="lfgm2026", help="Diagnostic login password")
    args = parser.parse_args()
    
    report = asyncio.run(run_audit(args.host, args.user, args.password))
    
    # Save the audit report locally
    report_file = Path("audit_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"SUCCESS: Diagnostic report saved to {report_file.resolve()}")
