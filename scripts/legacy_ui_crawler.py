import asyncio
from playwright.async_api import async_playwright
import os
import glob
import subprocess
import time
import sys

APIARY_ROOT = "/home/james/stacklabs"
OUTPUT_DIR = os.path.join(APIARY_ROOT, "uat_screenshots")
PORT = 8098

def find_html_files():
    # Gather root .html files
    root_files = glob.glob(os.path.join(APIARY_ROOT, "*.html"))
    # Gather /ui_archive/ .html files - use recursive just in case there are nested structures
    archive_files = glob.glob(os.path.join(APIARY_ROOT, "ui_archive", "**", "*.html"), recursive=True)
    return list(set(root_files + archive_files))

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    html_files = find_html_files()
    
    if not html_files:
        print("No HTML files found in root or /ui_archive/.")
        return

    # Start local HTTP server
    print(f"Starting HTTP server at {APIARY_ROOT} on port {PORT}...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT)],
        cwd=APIARY_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2) # Give it 2 seconds to bind and start

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()

            for file_path in html_files:
                # Convert absolute path to localhost URL
                rel_path = os.path.relpath(file_path, APIARY_ROOT)
                url = f"http://127.0.0.1:{PORT}/{rel_path}"
                
                # Naming convention [OriginalFileName]_screenshot.png
                original_filename = os.path.basename(file_path)
                screenshot_filename = f"{original_filename}_screenshot.png"
                screenshot_path = os.path.join(OUTPUT_DIR, screenshot_filename)
                
                print(f"Crawling {url} ({original_filename}) ...")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                except Exception as e:
                    print(f"Timeout/Error waiting for networkidle on {original_filename}: {e}")
                
                # Allow an extra 2 seconds for JS execution, canvases, CSS animations to settle
                await asyncio.sleep(2) 
                
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"Captured: {screenshot_path}")

            await browser.close()
    finally:
        server_process.terminate()
        server_process.wait()
        print("HTTP server process safely terminated.")

if __name__ == "__main__":
    asyncio.run(main())
