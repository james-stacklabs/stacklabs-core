#!/usr/bin/env python3
"""
SOVEREIGN OS: Portal 2.0 UAT DOM Crawler
Agent: Antigravity / Ferris Structural QA Protocol
Target: http://clio.taila01894.ts.net:8000/sovereign_employee_center.html
Output: /mnt/ghost_drive/uat_captures/
"""
import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TARGET_URL = "http://clio.taila01894.ts.net:8000/sovereign_employee_center.html"
UAT_DIR    = "/mnt/ghost_drive/uat_captures"
API_BASE   = "http://clio.taila01894.ts.net:8082"
TIMESTAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")

TABS = [
    {"id": "home",   "selector": "div.nav-link[data-target='home']"},
    {"id": "kanban", "selector": "div.nav-link[data-target='kanban']"},
    {"id": "fleet",  "selector": "div.nav-link[data-target='fleet']"},
    {"id": "b2b",    "selector": "div.nav-link[data-target='b2b']"},
    {"id": "cmdb",   "selector": "div.nav-link[data-target='cmdb']"},
]

# Endpoints to audit directly via HTTP
AUDIT_ENDPOINTS = [
    "/api/status",
    "/api/tickets",
    "/api/nodes",
    "/api/cmdb",
    "/api/cmdb/save",
    "/api/cortex/log",
    "/api/cortex/export",
]

os.makedirs(UAT_DIR, exist_ok=True)
network_log = []
broken_bindings = []

def log(msg):
    print(f"[CRAWLER] {msg}")

def run_crawler():
    log(f"Starting UAT session — {TIMESTAMP}")
    log(f"Target: {TARGET_URL}")
    log(f"Artifacts → {UAT_DIR}")
    print("─" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # ── NETWORK INTERCEPT ────────────────────────────────────────────────
        def on_response(response):
            url = response.url
            if "/api/" in url:
                status = response.status
                entry = {
                    "url": url,
                    "status": status,
                    "ok": response.ok
                }
                network_log.append(entry)
                if not response.ok:
                    broken_bindings.append(entry)
                    log(f"  ⚠️  BROKEN → [{status}] {url}")

        page.on("response", on_response)

        # ── LOAD PAGE ────────────────────────────────────────────────────────
        log("Loading portal...")
        try:
            page.goto(TARGET_URL, timeout=15000, wait_until="networkidle")
        except PlaywrightTimeoutError:
            log("WARNING: Page did not reach network idle — proceeding anyway.")
        
        # Initial screenshot (page load state)
        init_shot = os.path.join(UAT_DIR, f"{TIMESTAMP}_00_INITIAL_LOAD.png")
        page.screenshot(path=init_shot, full_page=True)
        log(f"  📸 Captured: 00_INITIAL_LOAD.png")

        # ── TAB TRAVERSAL ────────────────────────────────────────────────────
        for i, tab in enumerate(TABS, start=1):
            log(f"  → Activating tab: {tab['id'].upper()}")
            try:
                page.click(tab["selector"])
                # Wait for any API calls from the tab to settle
                page.wait_for_load_state("networkidle", timeout=5000)
            except PlaywrightTimeoutError:
                pass  # Tab may not trigger network requests

            shot_path = os.path.join(UAT_DIR, f"{TIMESTAMP}_{i:02d}_{tab['id'].upper()}.png")
            page.screenshot(path=shot_path, full_page=True)
            log(f"  📸 Captured: {i:02d}_{tab['id'].upper()}.png")

        browser.close()
        log("Browser session closed.")

    # ── DIRECT API AUDIT ─────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    log("Running direct REST endpoint audit...")
    import urllib.request
    import urllib.error

    audit_results = []
    for endpoint in AUDIT_ENDPOINTS:
        full_url = f"{API_BASE}{endpoint}"
        method = "POST" if endpoint in ["/api/cmdb/save", "/api/cortex/log", "/api/cortex/export"] else "GET"
        
        try:
            req = urllib.request.Request(full_url, method=method)
            # Add dummy payload for POSTs so we don't get 400 Empty Body
            if method == "POST":
                req.add_header('Content-Length', '2')
                req.data = b"{}"

            with urllib.request.urlopen(req, timeout=3) as r:
                status = r.status
                ok = True
        except urllib.error.HTTPError as e:
            status = e.code
            ok = False
        except Exception as e:
            status = 0
            ok = False

        symbol = "✅" if ok else "❌"
        label  = "OK" if ok else "BROKEN"
        audit_results.append({"endpoint": endpoint, "status": status, "ok": ok})
        log(f"  {symbol} [{status}] {endpoint} — {label}")

    # ── WRITE REPORT ─────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    report = {
        "timestamp": TIMESTAMP,
        "target_url": TARGET_URL,
        "tabs_captured": [t["id"] for t in TABS],
        "screenshots_dir": UAT_DIR,
        "network_intercept_log": network_log,
        "broken_bindings_from_dom": broken_bindings,
        "direct_api_audit": audit_results,
        "summary": {
            "total_api_calls_from_dom": len(network_log),
            "broken_from_dom": len(broken_bindings),
            "direct_endpoints_tested": len(audit_results),
            "direct_endpoints_broken": len([r for r in audit_results if not r["ok"]])
        }
    }

    report_path = os.path.join(UAT_DIR, f"{TIMESTAMP}_uat_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print()
    log("=" * 70)
    log(f"UAT COMPLETE")
    log(f"  Screenshots     : {len(TABS) + 1} captured in {UAT_DIR}")
    log(f"  DOM API calls   : {len(network_log)} intercepted")
    log(f"  Broken bindings : {len(broken_bindings)} (DOM intercept)")
    log(f"  Direct broken   : {len([r for r in audit_results if not r['ok']])} / {len(audit_results)} endpoints")
    log(f"  Full report     : {report_path}")
    log("=" * 70)

if __name__ == "__main__":
    run_crawler()
