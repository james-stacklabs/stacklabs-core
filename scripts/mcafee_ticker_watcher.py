#!/usr/bin/env python3
"""
MCAFEE ON-AIR TICKER OCR WATCHER (Tool #51 / Tool #59)
Screenshots the lower-third SeatGeek chyron on Pat McAfee's live YouTube stream
every 10s and extracts verbatim ticker text via tesseract-ocr.
Relays extracted tickers to WebSocket (ws://127.0.0.1:8008) and appends to
/home/james/sovereign_inbox/today/mcafee_ticker_feed.jsonl.
"""

import asyncio
import time
import subprocess
import json
import os
import sys
import websockets
from playwright.async_api import async_playwright

VIDEO_ID = "fa_CN7JKMCY"
OUTPUT_FEED = "/home/james/stacklabs_inbox/today/mcafee_ticker_feed.jsonl"
WS_URL = "ws://127.0.0.1:8008"

async def run_ticker(video_id=VIDEO_ID):
    os.makedirs(os.path.dirname(OUTPUT_FEED), exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        print(f"[TickerWatcher] Navigating to https://www.youtube.com/watch?v={video_id} ...", flush=True)
        await page.goto(f"https://www.youtube.com/watch?v={video_id}", wait_until="domcontentloaded")
        await asyncio.sleep(4)
        
        # Inject CSS to eradicate YouTube player controls/overlays
        await page.add_style_tag(content="""
            .ytp-chrome-bottom, .ytp-chrome-top, .ytp-gradient-bottom, .ytp-gradient-top {
                display: none !important;
            }
        """)
        await page.mouse.move(0, 0)
        
        last_text = ""
        print("[TickerWatcher] Started OCR polling loop (10s intervals)...", flush=True)
        while True:
            try:
                video = await page.query_selector('#movie_player')
                if video:
                    box = await video.bounding_box()
                    if box and box['width'] > 0 and box['height'] > 0:
                        clip = {
                            'x': box['x'],
                            'y': box['y'] + box['height'] - 42,
                            'width': box['width'],
                            'height': 42
                        }
                        img_bytes = await page.screenshot(clip=clip)
                        
                        # Run local tesseract OCR
                        proc = subprocess.run(
                            ["tesseract", "stdin", "stdout", "--oem", "1", "-l", "eng"],
                            input=img_bytes,
                            capture_output=True
                        )
                        raw_text = proc.stdout.decode('utf-8', errors='ignore').strip()
                        clean_text = raw_text.replace("SEATGEEK TICKER", "").replace("TICKER", "").strip()
                        
                        if clean_text and len(clean_text) > 8 and clean_text != last_text:
                            last_text = clean_text
                            t_str = time.strftime("%H:%M:%S")
                            entry = {
                                "id": f"ocr-{int(time.time())}",
                                "timestamp": t_str,
                                "type": "MCAFEE_TICKER",
                                "subtype": "ON_AIR_OCR",
                                "text": clean_text
                            }
                            # Append to JSONL
                            with open(OUTPUT_FEED, "a", encoding="utf-8") as f:
                                f.write(json.dumps(entry) + "\n")
                                
                            # Relay to WebSocket
                            try:
                                async with websockets.connect(WS_URL) as ws:
                                    await ws.send(json.dumps(entry))
                            except Exception:
                                pass
                                
                            print(f"[{t_str}] [TICKER OCR] {clean_text}", flush=True)
            except Exception as e:
                print(f"Ticker loop err: {e}", flush=True)
            await asyncio.sleep(10)

if __name__ == "__main__":
    target_vid = sys.argv[1] if len(sys.argv) > 1 else VIDEO_ID
    try:
        asyncio.run(run_ticker(target_vid))
    except KeyboardInterrupt:
        print("[TickerWatcher] Stopping...")
