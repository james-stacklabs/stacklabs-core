#!/home/james/stacklabs/.venv/bin/python3
"""
Headless Playwright 1920x1080 Viewport Snapshot Harness for Visual Vision UAT Gate.
Usage: /home/james/stacklabs/.venv/bin/python3 playwright_snapshot.py <url_or_route> <output_png_path>
"""

import os
import sys
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv("/home/james/stacklabs/.env")


def capture_snapshot(route_or_url: str, output_png: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(output_png)), exist_ok=True)
    base_port = os.getenv("FAAS_PORT", "3033")
    if route_or_url.startswith("http://") or route_or_url.startswith("https://"):
        target_url = route_or_url
    elif route_or_url.startswith("/") or route_or_url.startswith("?"):
        sep = "" if route_or_url.startswith("/") else "/"
        target_url = f"http://127.0.0.1:{base_port}{sep}{route_or_url}"
    else:
        target_url = f"http://127.0.0.1:{base_port}/?view={route_or_url}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            color_scheme="dark",
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(3.5)

        if page.locator("#auth-username").count() > 0:
            try:
                page.fill("#auth-username", os.getenv("COCKPIT_USER", "james"))
                page.fill("#auth-password", os.getenv("COCKPIT_PASS", "!!Stella1977"))
                page.click("#auth-submit")
                time.sleep(3.5)
            except Exception:
                pass

        page.screenshot(path=output_png, full_page=False)
        browser.close()
    print(f"[+] Captured 1920x1080 viewport snapshot: {output_png} ({target_url})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: /home/james/stacklabs/.venv/bin/python3 playwright_snapshot.py <route_or_url> <output_png>")
        sys.exit(1)
    capture_snapshot(sys.argv[1], sys.argv[2])
