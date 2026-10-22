#!/home/james/stacklabs/.venv/bin/python3
import sys
import os
import re
import json
import sqlite3
import asyncio
import argparse
from datetime import datetime
from playwright.async_api import async_playwright

sys.path.insert(0, '/home/james/stacklabs/scripts')
from core.api_client import resolve_team_name, get_team

# Database configuration
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
STREAMEAST_DEFAULT_BASE = "https://www.streameast.is"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

async def scrape_stream_page(url, dry_run=False):
    """
    Launches Playwright headless Chromium to load the StreamEast page,
    bypasses Cloudflare, intercepts requests to extract the m3u8 link and headers.
    """
    print(f"[*] Initializing Playwright stealth browser targeting: {url}")
    m3u8_url = None
    stream_headers = {}

    async with async_playwright() as p:
        # Launch browser with options to bypass basic automation checks
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )

        page = await context.new_page()

        # Remove webdriver descriptor
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Request Interceptor
        def handle_request(request):
            nonlocal m3u8_url, stream_headers
            req_url = request.url
            if ".m3u8" in req_url and not m3u8_url:
                print(f"[+] Intercepted m3u8 Master Feed URL: {req_url}")
                m3u8_url = req_url
                # Save request headers
                stream_headers = dict(request.headers)
                # Ensure Referer is set correctly if it wasn't intercepted
                if "referer" not in [k.lower() for k in stream_headers.keys()]:
                    stream_headers["Referer"] = url

        page.on("request", handle_request)

        try:
            print("[*] Navigating to StreamEast game page...")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for any Cloudflare verification redirects/JS challenges
            print("[*] Waiting for potential Cloudflare challenge or JS redirection...")
            await page.wait_for_timeout(10000)

            # Interact with the page to trigger the player to stream (simulates user clicks on overlay play buttons)
            print("[*] Attempting page clicks to dismiss player overlays and trigger stream...")
            # Click the player area or body center
            await page.click("body", position={"x": 960, "y": 540})
            await page.wait_for_timeout(3000)

            # Try clicking inside iframe elements if found
            for frame in page.frames:
                try:
                    video_el = await frame.query_selector("video")
                    if video_el:
                        await video_el.click()
                        print("[*] Clicked play button inside iframe player.")
                except Exception:
                    pass

            # Final wait to gather requests
            await page.wait_for_timeout(5000)

        except Exception as e:
            print(f"[!] Error during Playwright execution: {e}")
        finally:
            await browser.close()

    return m3u8_url, stream_headers

async def find_stream_url_from_home(home_team, away_team, base_url):
    """
    Navigates to the StreamEast home page, scans for links matching the team names,
    and returns the target page URL.
    """
    home_abbr = resolve_team_name(home_team)
    away_abbr = resolve_team_name(away_team)
    home_obj = get_team(home_abbr) or {}
    away_obj = get_team(away_abbr) or {}
    home_name = (home_obj.get("name") or home_team).lower()
    away_name = (away_obj.get("name") or away_team).lower()
    print(f"[*] Scanning {base_url} home page for game link ({away_name} vs {home_name})...")
    
    target_link = None
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = await context.new_page()
        try:
            await page.goto(base_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Scrape links
            links = await page.query_selector_all("a")
            for link in links:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                
                if href:
                    href_lower = href.lower()
                    text_lower = text.lower() if text else ""
                    
                    # Look for links containing both teams or the names under /mlb/
                    if "/mlb/" in href_lower or "mlb" in href_lower:
                        if (home_name in href_lower or home_name in text_lower) and \
                           (away_name in href_lower or away_name in text_lower):
                            target_link = href if href.startswith("http") else f"{base_url.rstrip('/')}{href}"
                            print(f"[+] Found match in links: {text} -> {target_link}")
                            break
        except Exception as e:
            print(f"[!] Error scanning home page links: {e}")
        finally:
            await browser.close()
            
    return target_link

async def process_game(game_id, home_team, away_team, base_url, dry_run=False):
    """
    Runs the full scraping sequence for a given game.
    """
    print(f"\n[*] PROCESSING GAME: {away_team} @ {home_team} (ID: {game_id})")
    
    # Step 1: Find game URL on StreamEast
    target_url = await find_stream_url_from_home(home_team, away_team, base_url)
    
    # Fallback to constructed guess URL if none found on home page
    if not target_url:
        home_abbr = resolve_team_name(home_team)
        away_abbr = resolve_team_name(away_team)
        home_obj = get_team(home_abbr) or {}
        away_obj = get_team(away_abbr) or {}
        home_slug = (home_obj.get("name") or home_team).lower().replace(" ", "-")
        away_slug = (away_obj.get("name") or away_team).lower().replace(" ", "-")
        target_url = f"{base_url}/mlb/{away_slug}-at-{home_slug}"
        print(f"[!] Target link not found on home page. Trying constructed fallback URL: {target_url}")
        
    # Step 2: Scrape the page
    m3u8_url, headers = await scrape_stream_page(target_url, dry_run)
    
    if m3u8_url:
        print(f"[+] SUCCESS: Extracted HLS stream URL: {m3u8_url}")
        headers_json = json.dumps(headers)
        
        if dry_run:
            print(f"[DRY-RUN] Would update game {game_id} in database:")
            print(f"  stream_url = {m3u8_url}")
            print(f"  stream_headers = {headers_json}")
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE mlb_schedule
                    SET stream_url = ?,
                        stream_source = 'StreamEast',
                        stream_headers = ?,
                        stream_resolved_at = datetime('now')
                    WHERE game_pk = ?
                """, (m3u8_url, headers_json, game_id))
                conn.commit()
                conn.close()
                print(f"[+] Database updated for game {game_id}")
            except Exception as db_err:
                print(f"[!] Database update failed: {db_err}")
    else:
        print(f"[!] FAILED: Could not extract m3u8 stream for game {game_id}")

async def main():
    parser = argparse.ArgumentParser(description="Headless HLS Stream Scraper Daemon")
    parser.add_argument("--dry-run", action="store_true", help="Perform scraping without database modifications")
    parser.add_argument("--url", type=str, help="Directly scrape a specific target stream URL")
    parser.add_argument("--game-id", type=str, help="Target game_pk when utilizing a direct URL")
    parser.add_argument("--base-url", type=str, default=STREAMEAST_DEFAULT_BASE, help="Override StreamEast base URL")
    
    args = parser.parse_args()
    
    if args.url:
        # Direct URL mode
        game_id = args.game_id or "999999"
        m3u8_url, headers = await scrape_stream_page(args.url, args.dry_run)
        if m3u8_url:
            print(f"[+] SUCCESS: Extracted HLS stream URL: {m3u8_url}")
            headers_json = json.dumps(headers)
            
            if args.dry_run:
                print(f"[DRY-RUN] Would update game {game_id} in database:")
                print(f"  stream_url = {m3u8_url}")
                print(f"  stream_headers = {headers_json}")
            else:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE mlb_schedule
                        SET stream_url = ?,
                            stream_source = 'StreamEast',
                            stream_headers = ?,
                            stream_resolved_at = datetime('now')
                        WHERE game_pk = ?
                    """, (m3u8_url, headers_json, game_id))
                    conn.commit()
                    conn.close()
                    print(f"[+] Database updated for game {game_id}")
                except Exception as db_err:
                    print(f"[!] Database update failed: {db_err}")
        else:
            print(f"[!] FAILED: Could not extract m3u8 stream from URL {args.url}")
            sys.exit(1)
            
    else:
        # Standard Active Game Scan mode
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Find active or staged games for today
            today_str = datetime.today().strftime("%Y-%m-%d")
            cursor.execute("""
                SELECT game_pk, home_team, away_team 
                FROM mlb_schedule 
                WHERE game_date = ? AND (room_state = 'active' OR status IN ('LIVE', 'In Progress', 'Scheduled'))
            """, (today_str,))
            active_games = cursor.fetchall()
            conn.close()
        except Exception as e:
            print(f"[!] Database check failed: {e}")
            sys.exit(1)
            
        if not active_games:
            print("[*] No active or scheduled games found for today.")
            return
            
        print(f"[*] Found {len(active_games)} candidate games for today. Running scraping sweep...")
        for game in active_games:
            await process_game(
                game_id=str(game["game_pk"]),
                home_team=game["home_team"],
                away_team=game["away_team"],
                base_url=args.base_url,
                dry_run=args.dry_run
            )

if __name__ == "__main__":
    asyncio.run(main())
