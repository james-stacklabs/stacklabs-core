#!/usr/bin/env python3
"""
scripts/verify_wo0010951_retina_market_ticker.py
Verification script for WO0010951:
- Verifies /data/market_ticker.json endpoint returns HTTP 200 and >= 8 valid symbols
- Verifies #retina-footer-ticker presence and ticker items in DOM
- Captures desktop (1920x1080) and mobile (390x844) visual twins to mockups/
"""

import asyncio
import json
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:3028"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")

def verify_json_endpoint():
    url = f"{BASE_URL}/data/market_ticker.json"
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Expected 200 OK, got {resp.status}"
        data = json.loads(resp.read().decode())
    
    assert "items" in data, "market_ticker.json missing 'items'"
    items = data["items"]
    assert len(items) >= 8, f"Expected at least 8 tickers, got {len(items)}"
    for item in items:
        assert "symbol" in item and len(item["symbol"]) > 0, f"Invalid symbol: {item}"
        assert "price" in item and item["price"] > 0, f"Invalid price: {item}"
        assert "pct" in item, f"Invalid pct: {item}"
        assert "up" in item, f"Invalid up flag: {item}"
    print(f"[VERIFY JSON] PASS: Found {len(items)} tickers in {url}")
    return items

async def run_visual_audit():
    MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
    desktop_twin = MOCKUPS_DIR / "retina_wo0010951_desktop.png"
    mobile_twin = MOCKUPS_DIR / "retina_wo0010951_mobile.png"

    print(f"[VERIFY PLAYWRIGHT] Starting browser audit against {BASE_URL}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )

        # 1. Desktop Viewport (1920x1080)
        ctx_desktop = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page_d = await ctx_desktop.new_page()

        resp = await page_d.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
        assert resp and resp.status == 200, f"Expected 200, got {resp.status if resp else 'None'}"

        # Wait for footer ticker to render
        footer = await page_d.wait_for_selector("#retina-footer-ticker", timeout=5000)
        assert footer, "#retina-footer-ticker not found in DOM"

        # Wait for ticker items to populate
        await page_d.wait_for_selector(".ticker-item", timeout=10000)
        await asyncio.sleep(1.0)
        ticker_items = await page_d.query_selector_all(".ticker-item")
        assert len(ticker_items) > 0, "No .ticker-item elements rendered in marquee"

        # Check badge text
        lead_badge = await page_d.text_content(".ticker-lead-badge")
        assert "MARKETS // LIVE INGRESS" in lead_badge, f"Unexpected badge text: {lead_badge}"

        # Take desktop screenshot
        await page_d.screenshot(path=str(desktop_twin), full_page=True)
        print(f"[VERIFY PLAYWRIGHT] Desktop screenshot captured -> {desktop_twin}")

        # 2. Mobile Viewport (390x844)
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1
        )
        page_m = await ctx_mobile.new_page()
        await page_m.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
        await page_m.wait_for_selector("#retina-footer-ticker", timeout=5000)
        await page_m.wait_for_selector(".ticker-item", timeout=10000)
        await asyncio.sleep(0.5)
        await page_m.screenshot(path=str(mobile_twin), full_page=True)
        print(f"[VERIFY PLAYWRIGHT] Mobile screenshot captured -> {mobile_twin}")

        await browser.close()

if __name__ == "__main__":
    verify_json_endpoint()
    asyncio.run(run_visual_audit())
    print("[VERIFY] ALL ACCEPTANCE CRITERIA PASSED.")
