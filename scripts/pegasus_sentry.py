#!/usr/bin/env python3
"""
Pegasus Visual Sentry Agent (Playwright Headless Node)
Path: ~/sovereign_sentry/pegasus_sentry.py
Node: pegasus (100.96.77.20)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright

async def run_inspection(url: str, output_path: str, width: int = 1920, height: int = 1080, wait_ms: int = 3000, click_selector: str = None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            ignore_https_errors=True,
            user_agent="Sovereign-Pegasus-VisualSentry/1.0"
        )
        page = await context.new_page()
        
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        start_time = datetime.now()
        load_ok = True
        error_msg = None
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=20000)
        except Exception as e:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except Exception as e2:
                load_ok = False
                error_msg = str(e2)
                
        if click_selector:
            try:
                await page.wait_for_selector(click_selector, timeout=8000)
                await page.click(click_selector)
                await page.wait_for_timeout(1000)
            except Exception as ce:
                console_logs.append(f"[warning] Failed to click {click_selector}: {ce}")

        await page.wait_for_timeout(wait_ms)
        
        page_title = await page.title()
        
        # Check KI-095 Locked Viewport & Zero Outer Scrollbars Mandate
        ki095_metrics = await page.evaluate("""() => {
            return {
                scrollHeight: document.documentElement.scrollHeight,
                clientHeight: document.documentElement.clientHeight,
                windowHeight: window.innerHeight,
                scrollWidth: document.documentElement.scrollWidth,
                windowWidth: window.innerWidth,
                hasVerticalScroll: document.documentElement.scrollHeight > window.innerHeight,
                hasHorizontalScroll: document.documentElement.scrollWidth > window.innerWidth
            };
        }""")
        
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        await page.screenshot(path=output_path, full_page=False)
        await browser.close()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        is_ki095 = not ki095_metrics["hasVerticalScroll"] and not ki095_metrics["hasHorizontalScroll"]
        errors = [l for l in console_logs if "[error]" in l.lower()]
        
        report = {
            "status": "PASS" if load_ok else "FAIL",
            "node": "pegasus (Intel i7-4790K)",
            "url": url,
            "page_title": page_title,
            "viewport": f"{width}x{height}",
            "duration_sec": round(duration, 2),
            "screenshot": output_path,
            "screenshot_bytes": os.path.getsize(output_path) if os.path.exists(output_path) else 0,
            "ki095_compliant": is_ki095,
            "ki095_metrics": ki095_metrics,
            "console_errors_count": len(errors),
            "console_errors": errors[:5],
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        
        return report

def main():
    parser = argparse.ArgumentParser(description="Pegasus Visual Sentry")
    parser.add_argument("--url", required=True, help="Target portal URL")
    parser.add_argument("--out", required=True, help="Output screenshot PNG path")
    parser.add_argument("--width", type=int, default=1920, help="Viewport width")
    parser.add_argument("--height", type=int, default=1080, help="Viewport height")
    parser.add_argument("--wait", type=int, default=3000, help="Post-load wait in ms")
    parser.add_argument("--click", default=None, help="Optional selector to click after page load")
    
    args = parser.parse_args()
    report = asyncio.run(run_inspection(args.url, args.out, args.width, args.height, args.wait, args.click))
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
