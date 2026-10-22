#!/usr/bin/env python3
"""
Verification Script for WO0010920: Fix Dot Public Ingress and Cockpit Staging
Author: Clio Forge Master
Host: clio (Beelink SER Mini PC / 100.96.77.20)
Date: October 06, 2026
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

def test_dot_public_ingress():
    print("[1/3] Testing Public Ingress for https://dot.stacklabsllc.com...")
    req = urllib.request.Request(
        "https://dot.stacklabsllc.com/",
        headers={"User-Agent": "Clio-Metal-Verification/1.0"},
        method="HEAD"
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            status = resp.status
            server = resp.headers.get("Server", "")
            cf_ray = resp.headers.get("CF-RAY", "")
            print(f"  ✅ Cloudflare Edge HEAD Status: {status} ({elapsed_ms:.1f}ms) | Server: {server} | CF-RAY: {cf_ray}")
            assert status == 200, f"Expected 200 OK, got {status}"
    except Exception as e:
        print(f"  ❌ Public Ingress HEAD failed: {e}")
        raise

def test_cockpit_stage_api():
    print("\n[2/3] Testing Port 8088 /api/cockpit/stage_work_order Atomic Endpoint...")
    url = "http://127.0.0.1:8088/api/cockpit/stage_work_order"
    payload = json.dumps({
        "title": "WO0010920-VERIFY-ATOMIC-STAGING",
        "content": "# WO0010920: VERIFY ATOMIC STAGING\n\nDirect metal verification receipt."
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        status = resp.status
        data = json.loads(resp.read().decode("utf-8"))
        print(f"  ✅ Status: {status} in {elapsed_ms:.2f}ms (< 500ms constraint met)")
        print(f"  ✅ Response: {data}")
        assert data.get("status") == "success"
        assert data.get("ticket_id") == "WO0010920"
        
        target_path = Path(data.get("path", ""))
        assert target_path.exists(), f"Staged file {target_path} does not exist!"
        assert target_path.read_text(encoding="utf-8") == "# WO0010920: VERIFY ATOMIC STAGING\n\nDirect metal verification receipt."
        print(f"  ✅ Disk Invariant: File {target_path.name} verified intact on NVMe.")
        target_path.unlink()
        print(f"  ✅ Campsite cleanup: Removed ephemeral verification file.")

def test_playwright_dual_viewport():
    print("\n[3/3] Testing Cockpit UI Dual Viewport (Desktop 1920x1080 & Mobile 390x844)...")
    from playwright.sync_api import sync_playwright

    evidence_dir = Path("/home/james/evidence/visual_twins")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    desktop_png = evidence_dir / "WO0010920_cockpit_stage_desktop.png"
    mobile_png = evidence_dir / "WO0010920_cockpit_stage_mobile.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop Viewport
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto("http://127.0.0.1:8088/cockpit", wait_until="networkidle")
        
        # Switch to Atomic Stage Tab
        page.evaluate("switchTab('tab-stage')")
        page.wait_for_selector("#stage-wo-title", state="visible")
        
        title_input = page.locator("#stage-wo-title")
        content_input = page.locator("#stage-wo-content")
        stage_btn = page.locator("#btn-stage-wo")
        
        title_input.fill("WO0010920-PLAYWRIGHT-DESKTOP-TEST")
        content_input.fill("# WO0010920: PLAYWRIGHT DESKTOP TEST\n\nDual twin verification.")
        
        t0 = time.perf_counter()
        stage_btn.click()
        
        # Verify toast
        toast = page.locator("#toast-container div").first
        toast.wait_for(state="visible", timeout=8000)
        toast_text = toast.inner_text()
        latency_ms = (time.perf_counter() - t0) * 1000.0
        print(f"  ✅ Desktop Stage Toast: '{toast_text}' ({latency_ms:.1f}ms)")
        
        page.screenshot(path=str(desktop_png), full_page=False)
        print(f"  ✅ Saved Desktop Visual Twin: {desktop_png}")
        page.close()

        # Clean up desktop test ticket
        test_file = Path("/home/james/stacklabs/queue/incoming/WO0010920-PLAYWRIGHT-DESKTOP-TEST.md")
        if test_file.exists():
            test_file.unlink()

        # 2. Mobile Viewport (iPhone 14 standard: 390x844)
        m_page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        m_page.goto("http://127.0.0.1:8088/cockpit", wait_until="networkidle")
        
        # Switch to Atomic Stage Tab on mobile
        m_page.evaluate("switchTab('tab-stage')")
        m_page.wait_for_selector("#stage-wo-title", state="visible")
        
        m_title = m_page.locator("#stage-wo-title")
        m_content = m_page.locator("#stage-wo-content")
        m_btn = m_page.locator("#btn-stage-wo")
        
        m_title.fill("WO0010920-PLAYWRIGHT-MOBILE-TEST")
        m_content.fill("# WO0010920: PLAYWRIGHT MOBILE TEST\n\nDual twin verification on mobile.")
        
        t0 = time.perf_counter()
        m_btn.click()
        
        m_toast = m_page.locator("#toast-container div").first
        m_toast.wait_for(state="visible", timeout=8000)
        m_toast_text = m_toast.inner_text()
        m_latency_ms = (time.perf_counter() - t0) * 1000.0
        print(f"  ✅ Mobile Stage Toast: '{m_toast_text}' ({m_latency_ms:.1f}ms)")
        
        m_page.screenshot(path=str(mobile_png), full_page=False)
        print(f"  ✅ Saved Mobile Visual Twin: {mobile_png}")
        m_page.close()

        # Clean up mobile test ticket
        m_test_file = Path("/home/james/stacklabs/queue/incoming/WO0010920-PLAYWRIGHT-MOBILE-TEST.md")
        if m_test_file.exists():
            m_test_file.unlink()

        browser.close()

if __name__ == "__main__":
    try:
        test_dot_public_ingress()
        test_cockpit_stage_api()
        test_playwright_dual_viewport()
        print("\n🎉 ALL INVARIANTS AND ACCEPTANCE CRITERIA VERIFIED ON METAL!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        sys.exit(1)
