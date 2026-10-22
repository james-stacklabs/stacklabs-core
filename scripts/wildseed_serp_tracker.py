#!/usr/bin/env python3
"""
WildSeed SERP Baseline & Daily Rank Tracker
Queries public search results across the 5 canonical WildSeed query baskets,
records positions, detects entity collisions with Marysville dispensary,
and saves the snapshot to JSON and Markdown.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
import re
import base64
import time

QUERIES = [
    "WildSeed Extracts",
    "WildSeed Extracts Humboldt",
    "Michael Mclaren living soil rosin",
    "WildSeed Extracts living soil cold cure live rosin",
    "WildSeed Extracts Arcata"
]

OUT_JSON = "/home/james/sovereign_inbox/today/WILDSEED_SERP_BASELINE_2026-09-22.json"
OUT_MD = "/home/james/sovereign_inbox/today/WILDSEED_SERP_TRACKER_CURRENT.md"

def fetch_duckduckgo_serp(query):
    # Primary: DDG HTML endpoint
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            res = parse_ddg_html(html)
            if res:
                return res
    except Exception as e:
        pass
        
    # High-reliability fallback 1: DDG Lite POST
    try:
        lite_url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": query}).encode()
        lite_req = urllib.request.Request(
            lite_url,
            data=data,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://lite.duckduckgo.com/"
            }
        )
        with urllib.request.urlopen(lite_req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            res = parse_ddg_lite(html)
            if res:
                return res
    except Exception as e:
        pass

    # High-reliability fallback 2: Bing Search
    try:
        bing_url = f"https://www.bing.com/search?q={encoded}"
        bing_req = urllib.request.Request(
            bing_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(bing_req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            return parse_bing_html(html)
    except Exception as e:
        print(f"[-] Multi-engine search error for '{query}': {e}")
        return []

def parse_ddg_html(html):
    results = []
    link_pattern = re.compile(r'<a class="result__url" href="([^"]+)".*?>(.*?)</a>', re.DOTALL)
    title_pattern = re.compile(r'<a class="result__a" href="([^"]+)".*?>(.*?)</a>', re.DOTALL)
    
    links = link_pattern.findall(html)
    titles = title_pattern.findall(html)
    
    for i, (href, title_text) in enumerate(titles[:15], 1):
        clean_title = re.sub(r'<.*?>', '', title_text).strip()
        actual_url = href
        if "uddg=" in href:
            match = re.search(r'uddg=([^&]+)', href)
            if match:
                actual_url = urllib.parse.unquote(match.group(1))
        
        results.append({
            "rank": i,
            "title": clean_title,
            "url": actual_url,
            "is_stacklabs": "stacklabsllc.com" in actual_url,
            "is_marysville": "wildseedwellness" in actual_url or "marysville" in actual_url.lower()
        })
    return results

def parse_ddg_lite(html):
    results = []
    pattern = re.compile(r"<a[^>]+href=['\"]([^'\"]+)['\"][^>]*class=['\"]result-link['\"][^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(html)
    if not matches:
        pattern2 = re.compile(r"<a[^>]+class=['\"]result-link['\"][^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
        matches = pattern2.findall(html)
        
    for i, (href, title_text) in enumerate(matches[:15], 1):
        clean_title = re.sub(r'<.*?>', '', title_text).strip()
        clean_title = clean_title.replace('&amp;', '&').replace('&quot;', '"').replace('&#x27;', "'").replace('&lt;', '<').replace('&gt;', '>')
        actual_url = href
        if "uddg=" in href:
            match = re.search(r'uddg=([^&]+)', href)
            if match:
                actual_url = urllib.parse.unquote(match.group(1))
        
        results.append({
            "rank": i,
            "title": clean_title,
            "url": actual_url,
            "is_stacklabs": "stacklabsllc.com" in actual_url,
            "is_marysville": "wildseedwellness" in actual_url or "marysville" in actual_url.lower()
        })
    return results

def parse_bing_html(html):
    results = []
    matches = list(re.finditer(r'<h2[^>]*><a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a></h2>', html))
    for i, m in enumerate(matches[:15], 1):
        raw_href = m.group(1)
        raw_title = m.group(2)
        clean_title = re.sub(r'<.*?>', '', raw_title).strip()
        clean_title = clean_title.replace('&amp;', '&').replace('&quot;', '"').replace('&#x27;', "'")
        
        # Decode Bing redirect url
        actual_url = raw_href
        norm_href = raw_href.replace('&amp;', '&')
        if '&u=' in norm_href:
            u_match = re.search(r'&u=([^&]+)', norm_href)
            if u_match:
                val = u_match.group(1)
                if val.startswith('a1'):
                    raw_b64 = val[2:]
                    pad = len(raw_b64) % 4
                    if pad:
                        raw_b64 += '=' * (4 - pad)
                    try:
                        actual_url = base64.b64decode(raw_b64).decode('utf-8', errors='ignore')
                    except Exception:
                        actual_url = norm_href
                        
        results.append({
            "rank": i,
            "title": clean_title,
            "url": actual_url,
            "is_stacklabs": "stacklabsllc.com" in actual_url,
            "is_marysville": "wildseedwellness" in actual_url or "marysville" in actual_url.lower()
        })
    return results

def main():
    now_iso = datetime.now(timezone.utc).isoformat()
    print(f"[*] Running WildSeed SERP Baseline Tracker: {now_iso}")
    snapshot = {
        "timestamp": now_iso,
        "queries": {}
    }
    
    md_lines = [
        f"# 📊 WILDSEED EMPIRICAL SERP BASELINE & TRACKER",
        f"> **Timestamp:** {now_iso}  ",
        f"> **Monitored Entity:** WildSeed Extracts (Michael Mclaren, Humboldt County, CA)  ",
        f"> **Target Live URL:** `https://www.stacklabsllc.com/wildseed`  ",
        f"> **Primary Competitor Collision:** Wild Seed Wellness (Marysville, CA)  ",
        "",
        "---",
        ""
    ]
    
    for q in QUERIES:
        print(f"[*] Querying: '{q}'...")
        res = fetch_duckduckgo_serp(q)
        snapshot["queries"][q] = res
        
        md_lines.append(f"### Query: `{q}`")
        if not res:
            md_lines.append("*No automated results returned or rate-limited on this run.*\n")
            continue
            
        md_lines.append("| Rank | Title | URL | Classification |")
        md_lines.append("| :--- | :---- | :-- | :------------- |")
        for r in res[:10]:
            cls = "Neutral"
            if r["is_stacklabs"]:
                cls = "**TARGET PORTAL (StackLabs)** ✅"
            elif r["is_marysville"]:
                cls = "⚠️ Marysville Retail Collision"
            md_lines.append(f"| #{r['rank']} | {r['title'][:40]} | `{r['url'][:50]}` | {cls} |")
        md_lines.append("")
        time.sleep(1.0)
    
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(snapshot, f, indent=2)
    with open(OUT_MD, "w") as f:
        f.write("\n".join(md_lines))
        
    print(f"[+] Baseline written to: {OUT_JSON}")
    print(f"[+] Report written to: {OUT_MD}")

if __name__ == "__main__":
    main()
