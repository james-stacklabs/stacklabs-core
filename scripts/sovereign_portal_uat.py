#!/usr/bin/env python3
"""
Sovereign OS — Full Site UAT Crawler
BFS link discovery across all Sovereign OS hosts + Vertex AI screenshot analysis.
Covers: clio.taila01894.ts.net (80/443) + :3009 (FanStack) + :3015 (AetherVet)
"""

import asyncio
import os
import re
import json
import zipfile
from datetime import datetime
from urllib.parse import urlparse, urljoin, urldefrag
from collections import deque
from playwright.async_api import async_playwright
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# ── CONFIG ───────────────────────────────────────────────────────────────────
OUT_DIR     = "/home/james/sovereign_inbox/today/uat_screenshots"
REPORT_PATH = "/home/james/sovereign_inbox/today/sovereign_uat_report.md"
ZIP_PATH    = "/home/james/sovereign_inbox/today/sovereign_uat_full.zip"
CREDS_PATH  = "/home/james/stacklabs/config/vertex_sa.json"
PROJECT_ID  = "gen-lang-client-0840454416"
LOCATION    = "us-central1"
MODEL_NAME  = "gemini-3.8-flash"
MAX_PAGES   = 30   # Safety cap — raise if needed

AUTH_USER = "james"
AUTH_PASS = "!!Stella1977"
SESSION_TOKEN = ""

# Hosts considered "internal" — crawl anything under these
ALLOWED_HOSTS = {
    "clio.taila01894.ts.net",       # main portal (80/443)
    "clio.taila01894.ts.net:3009",  # FanStack
    "clio.taila01894.ts.net:3010",  # Sovereign Sports
    "clio.taila01894.ts.net:3015",  # AetherVet
    "clio.taila01894.ts.net:3018",  # Inkwell & Irony Investigations
}

# BFS seed URLs — guaranteed starting points
SEEDS = [
    "https://clio.taila01894.ts.net/",
    "https://clio.taila01894.ts.net/prospectus.html",
    "https://clio.taila01894.ts.net:3009/",
    "https://clio.taila01894.ts.net:3009/?domain=MLB&room=scruffys",
    "https://clio.taila01894.ts.net:3009/?domain=MLB&room=roll_call",
    "https://clio.taila01894.ts.net:3009/fancast_fan_live_mobile.html",
    "https://clio.taila01894.ts.net:3009/fancast_live_logs.html",
    "https://clio.taila01894.ts.net:3010/fan-portal?game_room=824910",
    "https://clio.taila01894.ts.net:3010/creator-portal",
    "https://clio.taila01894.ts.net:3015/",
    "https://clio.taila01894.ts.net:3018/",
]

# Known SPA room slugs to inject as additional seeds after crawling root
FANSTACK_ROOMS = [
    "playcall_desk", "live_chat_sniper", "persona_center",
    "hot_takes", "highlight_heist", "god_mode",
    "scruffys", "the_press_box", "sam_tracker",
    "system_config", "argus", "cinema", "kanban",
    "tickets", "app_directory", "holo_link",
    "tmitv", "tmi_news_desk", "skew_studio",
]

# ── UTILS ────────────────────────────────────────────────────────────────────
def is_internal(url: str) -> bool:
    """Return True if the URL belongs to one of the allowed Sovereign OS hosts."""
    try:
        p = urlparse(url)
        host_with_port = p.netloc  # includes :port if present
        host_no_port   = p.hostname or ""
        return (host_with_port in ALLOWED_HOSTS or
                host_no_port in {h.split(":")[0] for h in ALLOWED_HOSTS})
    except:
        return False

def normalize_url(url: str) -> str:
    """Strip fragment so #sections don't create duplicates."""
    clean, _ = urldefrag(url)
    return clean.rstrip("/") if clean.endswith("/") and len(clean) > 8 else clean

def slug_from_url(url: str, index: int) -> str:
    p = urlparse(url)
    path_slug = re.sub(r"[^\w]", "_", (p.path + p.query))[:50].strip("_")
    port_tag  = f"p{p.port}" if p.port and p.port not in (80, 443) else "main"
    return f"{index:03d}_{port_tag}_{path_slug or 'root'}"

# ── AUTH ─────────────────────────────────────────────────────────────────────
async def inject_auth(page):
    """Inject all known auth tokens into localStorage."""
    eval_js = f"""
        localStorage.setItem('sov_auth', 'unlocked');
        localStorage.setItem('auth_token', 'sovereign_admin');
        localStorage.setItem('sovereign_user', 'james');
        localStorage.setItem('sovereign_role', 'admin');
        if ('{SESSION_TOKEN}') {{
            localStorage.setItem('sovereign_session_token', '{SESSION_TOKEN}');
        }}
    """
    await page.evaluate(eval_js)

async def handle_login_form(page):
    """If a login form is visible, fill and submit it."""
    try:
        u = await page.query_selector("#auth-username, input[type='text'], input[name='username'], #username")
        pw = await page.query_selector("#auth-password, input[type='password']")
        if u and pw:
            await u.fill(AUTH_USER)
            await pw.fill(AUTH_PASS)
            btn = await page.query_selector("#auth-submit, button[type='submit'], button:text('Login'), button:text('Sign In')")
            if btn:
                await btn.click()
                await page.wait_for_timeout(3000)
                return True
    except:
        pass
    return False

# ── LINK DISCOVERY ───────────────────────────────────────────────────────────
async def discover_links(page, base_url: str) -> set:
    """Extract all internal href links from the current page."""
    found = set()
    try:
        hrefs = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.href)"
        )
        for href in hrefs:
            url = normalize_url(href)
            if is_internal(url) and url.startswith("http"):
                found.add(url)
    except:
        pass

    # Also extract data-* navigation attributes (React SPA pattern)
    try:
        data_routes = await page.eval_on_selector_all(
            "[data-room], [data-domain], [data-route]",
            "els => els.map(e => ({room: e.dataset.room, domain: e.dataset.domain}))"
        )
        parsed = urlparse(base_url)
        base_root = f"{parsed.scheme}://{parsed.netloc}"
        for item in data_routes:
            if item.get("room"):
                room_url = f"{base_root}/?domain={item.get('domain', 'ROOT')}&room={item['room']}"
                found.add(normalize_url(room_url))
    except:
        pass

    return found

# ── VERTEX AI ────────────────────────────────────────────────────────────────
def analyze_screenshot(image_path: str, slug: str, desc: str) -> str:
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDS_PATH
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel(MODEL_NAME)

        with open(image_path, "rb") as f:
            data = f.read()
        if len(data) < 1000:
            return "⚠️ Screenshot too small — likely blank/error page."

        image_part = Part.from_data(data=data, mime_type="image/png")
        prompt = f"""You are a Senior QA Engineer performing a UAT audit of the Sovereign OS platform.

Page: {desc} | Slug: {slug}

Provide a structured UAT analysis:
1. **RENDER STATUS**: PASS / FAIL / PARTIAL
2. **AUTH STATE**: auth-wall / logged-in / public
3. **VISIBLE ELEMENTS**: major UI elements visible
4. **DATA LOADING**: live data / empty state / spinners / errors
5. **BROKEN ASSETS**: broken images, 404s, missing icons
6. **MOBILE READINESS**: responsive / not responsive
7. **INVESTOR READINESS**: 1–10 rating
8. **FLAGS**: specific bugs or concerns
9. **RECOMMENDATION**: DEMO READY / NEEDS WORK / BLOCKED

Be specific and factual."""

        response = model.generate_content([image_part, prompt])
        return response.text
    except Exception as e:
        return f"⚠️ Vertex AI analysis failed: {e}"

# ── MAIN CRAWLER ─────────────────────────────────────────────────────────────
async def run_crawl():
    global SESSION_TOKEN
    os.makedirs(OUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # BFS queue — normalize all seeds
    queue   = deque(normalize_url(s) for s in SEEDS)
    visited = set(normalize_url(s) for s in SEEDS)
    results = []

    print(f"[UAT] Sovereign OS Full-Site Crawl starting at {timestamp}")
    print(f"[UAT] Seeds: {len(queue)} | Max pages: {MAX_PAGES}")
    print(f"[UAT] Allowed hosts: {ALLOWED_HOSTS}\n")

    # Programmatic authentication token retrieval from core API running on port 8090
    try:
        import urllib.request
        url = "http://127.0.0.1:8090/api/auth/login"
        data = json.dumps({"username": AUTH_USER, "password": AUTH_PASS}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            SESSION_TOKEN = res_data.get("token") or ""
            print(f"[UAT AUTH] Programmatically retrieved JWT session token successfully!")
    except Exception as e:
        print(f"[UAT AUTH ERROR] Programmatic login failed: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors", "--disable-web-security", "--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )
        await context.add_init_script(f"""
            localStorage.setItem('sov_auth', 'unlocked');
            localStorage.setItem('auth_token', 'sovereign_admin');
            localStorage.setItem('sovereign_user', 'james');
            localStorage.setItem('sovereign_role', 'admin');
            if ('{SESSION_TOKEN}') {{
                localStorage.setItem('sovereign_session_token', '{SESSION_TOKEN}');
            }}
        """)

        page = await context.new_page()

        # Phase 1 — establish auth session on main portal
        print("[UAT] Phase 1: Auth session establishment...")
        try:
            await page.goto("https://clio.taila01894.ts.net/", wait_until="domcontentloaded", timeout=15000)
            await inject_auth(page)
            await page.reload(wait_until="domcontentloaded", timeout=10000)
            await handle_login_form(page)
            print("[UAT] Auth phase complete\n")
        except Exception as e:
            print(f"[UAT] Auth warning: {e}\n")

        # Also auth FanStack context
        try:
            await page.goto("https://clio.taila01894.ts.net:3009/", wait_until="domcontentloaded", timeout=10000)
            await inject_auth(page)
            await handle_login_form(page)
        except:
            pass

        # Also auth Sovereign Sports context
        try:
            await page.goto("https://clio.taila01894.ts.net:3010/fan-portal?game_room=824910", wait_until="domcontentloaded", timeout=10000)
            await inject_auth(page)
            await handle_login_form(page)
        except:
            pass

        # Phase 2 — inject SPA room seeds from known room slugs
        for room in FANSTACK_ROOMS:
            for domain in ["MLB", "ROOT"]:
                url = normalize_url(f"https://clio.taila01894.ts.net:3009/?domain={domain}&room={room}")
                if url not in visited:
                    visited.add(url)
                    queue.append(url)

        print(f"[UAT] Phase 2: Queue expanded to {len(queue)} URLs after SPA room injection\n")
        print("[UAT] Phase 3: BFS crawl starting...\n")

        page_index = 0

        while queue and page_index < MAX_PAGES:
            url = queue.popleft()
            page_index += 1
            slug = slug_from_url(url, page_index)

            print(f"[UAT] [{page_index:03d}/{MAX_PAGES}] {slug}")
            print(f"       URL: {url}")

            screenshot_path = os.path.join(OUT_DIR, f"{slug}.png")
            status = "UNKNOWN"
            analysis = ""
            error_msg = ""
            discovered = set()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2500)

                # Re-inject auth and handle login walls
                await inject_auth(page)
                body_text = await page.inner_text("body")
                if any(kw in body_text.lower() for kw in ["login", "sign in", "password", "unauthorized"]):
                    await handle_login_form(page)
                    await page.wait_for_timeout(2000)

                # Discover links from this page
                discovered = await discover_links(page, url)
                new_links = discovered - visited
                for link in new_links:
                    visited.add(link)
                    queue.append(link)
                if new_links:
                    print(f"       Discovered {len(new_links)} new link(s)")

                # Screenshot
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"       Screenshot → {slug}.png")

                # Vertex AI analysis
                print(f"       Analyzing with Vertex AI...")
                analysis = analyze_screenshot(screenshot_path, slug, url)

                if "PASS" in analysis[:200].upper() and "FAIL" not in analysis[:200].upper():
                    status = "PASS"
                elif "BLOCKED" in analysis[:200].upper():
                    status = "BLOCKED"
                elif "FAIL" in analysis[:200].upper():
                    status = "FAIL"
                elif "PARTIAL" in analysis[:200].upper():
                    status = "PARTIAL"
                else:
                    status = "REVIEWED"

                print(f"       Status: {status}\n")

            except Exception as e:
                error_msg = str(e)
                status = "ERROR"
                print(f"       ERROR: {e}\n")
                analysis = f"⚠️ Crawl error: {e}"
                try:
                    await page.screenshot(path=screenshot_path, full_page=True)
                except:
                    pass

            results.append({
                "index": page_index,
                "slug": slug,
                "url": url,
                "status": status,
                "screenshot": screenshot_path,
                "analysis": analysis,
                "error": error_msg,
                "discovered_count": len(discovered),
            })

        remaining = len(queue)
        await browser.close()

    print(f"\n[UAT] Crawl complete. {len(results)} pages captured. {remaining} URLs in queue (not visited).")

    # ── GENERATE REPORT ──────────────────────────────────────────────────────
    pass_c    = sum(1 for r in results if r["status"] == "PASS")
    fail_c    = sum(1 for r in results if r["status"] in ("FAIL", "BLOCKED", "ERROR"))
    partial_c = sum(1 for r in results if r["status"] == "PARTIAL")
    overall   = "🟢 DEMO READY" if fail_c == 0 else ("🟡 NEEDS REVIEW" if fail_c <= 3 else "🔴 BLOCKED")

    report = f"""# Sovereign OS — Full-Site UAT Report
**Generated:** {timestamp}
**Engine:** Playwright BFS Crawler + Vertex AI Gemini 2.5 Flash
**Scope:** Full site — `clio.taila01894.ts.net` (main + :3009 FanStack + :3015 AetherVet)

---

## Executive Status

| Metric | Value |
|---|---|
| **Total pages audited** | {len(results)} |
| **URLs in queue (not visited)** | {remaining} |
| **PASS** | {pass_c} |
| **PARTIAL** | {partial_c} |
| **FAIL / BLOCKED / ERROR** | {fail_c} |
| **Overall** | {overall} |

---

## Page Results

"""

    icon_map = {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠️", "BLOCKED": "🔴", "ERROR": "💥", "REVIEWED": "🔍", "UNKNOWN": "❓"}

    for r in results:
        icon = icon_map.get(r["status"], "❓")
        report += f"### {icon} [{r['index']:03d}] `{r['slug']}`\n\n"
        report += f"**URL:** `{r['url']}`  \n"
        report += f"**Status:** `{r['status']}`  \n"
        report += f"**Links discovered from this page:** {r['discovered_count']}\n\n"
        if os.path.exists(r["screenshot"]):
            report += f"![{r['slug']}]({r['screenshot']})\n\n"
        report += f"#### Vertex AI Analysis\n\n{r['analysis']}\n\n"
        if r["error"]:
            report += f"**Crawl error:** `{r['error']}`\n\n"
        report += "---\n\n"

    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(f"[UAT] Report → {REPORT_PATH}")

    # ── ZIP ──────────────────────────────────────────────────────────────────
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(REPORT_PATH, "sovereign_uat_report.md")
        for r in results:
            if os.path.exists(r["screenshot"]):
                zf.write(r["screenshot"], f"screenshots/{os.path.basename(r['screenshot'])}")
    print(f"[UAT] Archive → {ZIP_PATH} ({os.path.getsize(ZIP_PATH)//1024} KB)")

    # Quick summary
    print("\n=== FINAL RESULTS ===")
    for r in results:
        icon = icon_map.get(r["status"], "❓")
        print(f"  {icon} {r['slug']}: {r['status']}")

if __name__ == "__main__":
    asyncio.run(run_crawl())
