import asyncio
import os
import glob
import subprocess
import time
import argparse
from playwright.async_api import async_playwright

UAT_ROOT = "/home/james/stacklabs/uat_screenshots"
APIARY_ROOT = "/home/james/stacklabs"

async def capture_html_dirs(page, target_dirs, out_dir):
    print(f">>> CAPTURING THE CATACOMBS (PORT 8098) -> {target_dirs}")
    os.makedirs(out_dir, exist_ok=True)
    
    html_files = []
    for d in target_dirs:
        path_pattern = os.path.join(APIARY_ROOT, d, "*.html")
        html_files.extend(glob.glob(path_pattern))
        
    if not html_files:
        print(" -> No .html files found in standard scan. Checking recursively...")
        for d in target_dirs:
            path_pattern = os.path.join(APIARY_ROOT, d, "**", "*.html")
            html_files.extend(glob.glob(path_pattern, recursive=True))

    for file in html_files:
        # Avoid double captures if testing
        rel = os.path.relpath(file, APIARY_ROOT)
        url = f"http://127.0.0.1:8098/{rel}"
        print(f" -> {url}")
        
        try:
            await page.goto(url, wait_until="load", timeout=5000)
            await page.wait_for_timeout(500)
            
            # Create a safe filename preserving path
            safe_name = rel.replace("/", "_").replace("\\", "_") + ".png"
            filepath = os.path.join(out_dir, safe_name)
            
            await page.screenshot(path=filepath, full_page=True)
        except Exception as e:
            print(f"Failed to crawl {url}: {e}")

async def generate_pdf(page, out_dir, report_name):
    print(">>> COMPILING PDF ARTIFACT")
    html_out = os.path.join(out_dir, "pdf_manifest.html")
    pdf_out = os.path.join(UAT_ROOT, report_name)
    
    html_content = [
        "<html><head><style>",
        "h1 { font-family: monospace; background: #000; color: #0f0; padding: 10px; font-size: 14px; word-wrap: break-word; } ",
        "img { max-width: 100%; height: auto; page-break-after: always; display: block; border: 2px solid #ccc; }",
        "</style></head><body style='background: #fff; margin:0;'>"
    ]
    
    pngs = glob.glob(os.path.join(out_dir, "*.png"))
    for png in sorted(pngs):
        html_content.append(f"<h1>{os.path.basename(png)}</h1><img src='file://{png}' />")
            
    html_content.append("</body></html>")
    
    with open(html_out, "w") as f:
        f.write("\n".join(html_content))
        
    print(f" -> Rendering {html_out} to PDF...")
    await page.goto(f"file://{html_out}", wait_until="networkidle")
    await page.wait_for_timeout(1000)
    await page.pdf(path=pdf_out, format="A4", print_background=True)
    print(f" -> PDF Vaulted at {pdf_out}")

async def run(target_dirs, report_name):
    os.makedirs(UAT_ROOT, exist_ok=True)
    out_dir = os.path.join(UAT_ROOT, report_name.replace(".pdf", "_frames"))
    
    print(">>> STARTING LOCAL SERVER ON PORT 8098")
    server_process = subprocess.Popen(
        ["/home/james/stacklabs/.venv/bin/python", "-m", "http.server", "8098"], 
        cwd=APIARY_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
            
            await capture_html_dirs(page, target_dirs, out_dir)
            await generate_pdf(page, out_dir, report_name)
            
            await browser.close()
    finally:
        server_process.terminate()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FanStack Archaeological Crawler")
    parser.add_argument("dirs", nargs="+", help="List of directory paths relative to apiary root (e.g. UAT/08_FanStack DEV/08_FanStack)")
    parser.add_argument("--out", default="LEGACY_UI_AUDIT_REPORT_V2.pdf", help="Output PDF name inside uat_screenshots")
    args = parser.parse_args()
    
    asyncio.run(run(args.dirs, args.out))
