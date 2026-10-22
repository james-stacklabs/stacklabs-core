#!/usr/bin/env python3
"""
WildSeed Search Indexing Engine
Submits live WildSeed URLs to IndexNow (Bing, Yandex, Seznam), Google Sitemap Ping,
and Archive.org crawl queue to trigger rapid crawler ingress.
"""

import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

INDEXNOW_KEY = "4a8e9f2b1c7d3e5f6a0b8c9d1e2f3a4b"
HOST = "www.stacklabsllc.com"
URLS = [
    "https://www.stacklabsllc.com/wildseed",
    "https://www.stacklabsllc.com/wildseed#delivery",
    "https://www.stacklabsllc.com/wildseed#fieldnotes",
    "https://www.stacklabsllc.com/wildseed#saloon",
    "https://www.stacklabsllc.com/wildseed/wildseed_lookbook.pdf"
]

def submit_indexnow():
    print("[*] Submitting to IndexNow API (Bing/Yandex/Seznam)...")
    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{HOST}/wildseed/{INDEXNOW_KEY}.txt",
        "urlList": URLS
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[+] IndexNow Response: {resp.status} {resp.reason}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[-] IndexNow HTTP error: {e.code} {e.reason}")
        # Note: 200 or 202 is success. Even on key check latency, submission is queued.
        return False
    except Exception as e:
        print(f"[-] IndexNow exception: {e}")
        return False

def ping_google_sitemap():
    print("[*] Pinging Google sitemap...")
    sitemap_url = f"https://{HOST}/wildseed/sitemap.xml"
    ping_url = f"https://www.google.com/ping?sitemap={urllib.parse.quote(sitemap_url)}"
    try:
        req = urllib.request.Request(ping_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[+] Google Ping: {resp.status}")
            return True
    except Exception as e:
        print(f"[-] Google Ping note (endpoint may respond 404/redirect, logging): {e}")
        return False

def ping_bing_sitemap():
    print("[*] Pinging Bing sitemap...")
    sitemap_url = f"https://{HOST}/wildseed/sitemap.xml"
    ping_url = f"https://www.bing.com/ping?sitemap={urllib.parse.quote(sitemap_url)}"
    try:
        req = urllib.request.Request(ping_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[+] Bing Ping: {resp.status}")
            return True
    except Exception as e:
        print(f"[-] Bing Ping note: {e}")
        return False

def trigger_wayback_crawl():
    print("[*] Triggering Wayback Machine crawl queue...")
    target_url = f"https://{HOST}/wildseed"
    save_url = f"https://web.archive.org/save/{target_url}"
    try:
        req = urllib.request.Request(save_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[+] Wayback Crawl Triggered: {resp.status}")
            return True
    except Exception as e:
        print(f"[-] Wayback trigger note: {e}")
        return False

def main():
    print(f"=== WILDSEED SEARCH INDEXING DISPATCH ({datetime.utcnow().isoformat()}Z) ===")
    r1 = submit_indexnow()
    r2 = ping_google_sitemap()
    r3 = ping_bing_sitemap()
    r4 = trigger_wayback_crawl()
    print("=== DISPATCH COMPLETE ===")

if __name__ == "__main__":
    main()
