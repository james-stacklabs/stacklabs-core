import asyncio
import os
import time
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# Configuration
OUT_DIR = "/home/james/stacklabs/scratch/prospectus_screenshots"
REPORT_PATH = "/home/james/sovereign_inbox/today/Prospectus_Vertex_Deep_Crawl.md"
START_URL = "https://clio.taila01894.ts.net/?room=prospectus"
BASE_DOMAIN = "clio.taila01894.ts.net"
CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"
PROJECT_ID = "gen-lang-client-0840454416"
LOCATION = "us-central1"
MODEL_NAME = "gemini-3.8-flash"

def is_valid_url(url, base):
    parsed = urlparse(url)
    if not parsed.scheme:
        # Relative URL
        return True
    if parsed.netloc == BASE_DOMAIN or parsed.netloc.startswith(BASE_DOMAIN + ":"):
        return True
    return False

def analyze_image_with_vertex(image_path: str, url: str) -> str:
    print(f"[{url}] Analyzing with Vertex AI...")
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel(MODEL_NAME)
        
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        image_part = Part.from_data(data=image_data, mime_type="image/png")
        
        prompt = f"""
You are an expert QA automation bot. 
Analyze this screenshot of the URL: {url}.
Your ONLY goal is to detect if the page is broken, showing an error, or if there is a UI layout issue.
Specifically look for:
- "This site can't be reached" (ERR_CONNECTION_REFUSED)
- 404 Not Found
- 502 Bad Gateway
- Broken images, overlapping text, or obvious CSS rendering issues.
- Empty grey/black boxes that look like a component failed to load.

If you find an issue, explicitly say "ISSUE FOUND:" followed by the details.
If the page looks like a normal, healthy UI without obvious connection or loading errors, say "STATUS: OK" and give a 1-sentence summary of what the page is.
"""
        response = model.generate_content([image_part, prompt])
        parts_text = []
        if response and response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(part.text)
        if parts_text:
            return "".join(parts_text)
        try:
            return response.text
        except Exception:
            return "Empty response from Vertex AI"
    except Exception as e:
        return f"Error analyzing {url}: {e}"

async def run_crawl():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    
    report_content = "# Prospectus Deep Crawl Report\n\n"
    report_content += "Automated QA report by Vertex AI (`gemini-3.8-flash`) checking 2 levels deep.\n\n"
    
    visited = set()
    to_visit = [(START_URL, 0)]
    max_depth = 4
    
    results = []

    print("Launching headless browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        await context.add_init_script("window.localStorage.setItem('sov_auth', 'unlocked');")
        page = await context.new_page()
        
        while to_visit:
            current_url, depth = to_visit.pop(0)
            
            if current_url in visited:
                continue
                
            visited.add(current_url)
            print(f"[{depth}] Navigating to {current_url}...")
            
            try:
                # Add timeout and ignore network errors to capture what the browser actually sees (like ERR_CONNECTION_REFUSED)
                await page.goto(current_url, wait_until="networkidle", timeout=10000)
            except Exception as e:
                print(f"Warning: {e}")
            
            await page.wait_for_timeout(3000)
            
            # Check for login form and bypass it
            try:
                if await page.locator('#auth-username').is_visible(timeout=1000):
                    print(f"[{depth}] Detected auth gate, logging in as antigravity...")
                    await page.fill('#auth-username', 'antigravity')
                    await page.fill('#auth-password', 'lfgm2026')
                    await page.click('#auth-submit')
                    await page.wait_for_timeout(4000)
            except Exception as e:
                pass
            
            safe_filename = current_url.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "_").replace("?", "_").replace("=", "_")
            if not safe_filename:
                safe_filename = "root"
            image_path = os.path.join(OUT_DIR, f"{safe_filename}.png")
            await page.screenshot(path=image_path, full_page=True)
            print(f"Saved screenshot: {image_path}")
            
            analysis = analyze_image_with_vertex(image_path, current_url)
            results.append((current_url, depth, image_path, analysis))
            
            # Extract links if not at max depth
            if depth < max_depth:
                hrefs = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a')).map(a => a.href);
                }""")
                
                for href in hrefs:
                    if not href or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("#"):
                        continue
                    full_url = urljoin(current_url, href)
                    # Strip fragments
                    full_url = full_url.split('#')[0]
                    
                    if is_valid_url(full_url, current_url) and full_url not in visited:
                        to_visit.append((full_url, depth + 1))
            
        await browser.close()
        
    for url, depth, image_path, analysis in results:
        report_content += f"## Level {depth}: `{url}`\n\n"
        report_content += f"![Screenshot]({image_path})\n\n"
        report_content += f"### Vertex AI Analysis\n"
        report_content += f"{analysis}\n\n"
        report_content += "---\n\n"
            
    print(f"Writing report to {REPORT_PATH}...")
    with open(REPORT_PATH, "w") as f:
        f.write(report_content)
    print("Deep crawl complete!")

if __name__ == "__main__":
    asyncio.run(run_crawl())
