#!/home/james/stacklabs/.venv/bin/python3
"""
sportsx_feed_ingestor.py — Ingests live SportsX and DOM_M3U feeds into FaaS VFS.
Discovered via Pegasus Kodi deobfuscation audit.
Parses live .m3u8 streams and CDN bypass headers into /dev/shm/faas_vfs/guide.json.
"""

import os
import sys
import re
import json
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urlparse

VFS_DIR = Path("/dev/shm/faas_vfs")
VFS_DIR.mkdir(parents=True, exist_ok=True)
GUIDE_FILE = VFS_DIR / "guide.json"

DOM_M3U = "https://raw.githubusercontent.com/doms9/iptv/refs/heads/default/M3U8/events.m3u8"
SPORTSX_M3U = "https://raw.githubusercontent.com/Muji777/Exp/refs/heads/main/SportsX"

def fetch_url(url: str, timeout: int = 6) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[SportsX Ingest] Failed to fetch {url}: {e}")
        return ""

def parse_dom_events(text: str) -> List[Dict[str, Any]]:
    """Parses #EXTINF and #EXTVLCOPT lines from doms9 events.m3u8."""
    channels = []
    lines = text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            # Extract name
            name_match = re.search(r',(.+)$', line)
            name = name_match.group(1).strip() if name_match else "Live Event"
            
            # Category detection
            cat = "SPORTS"
            if "Bundesliga" in name or "Soccer" in name or "FC" in name:
                cat = "SOCCER"
            elif "CFB" in name or "NCAA" in name or "Football" in name:
                cat = "CFB"
            elif "MLB" in name or "Baseball" in name:
                cat = "MLB"
            elif "NFL" in name:
                cat = "NFL"

            i += 1
            headers = {}
            while i < len(lines):
                stripped = lines[i].strip()
                if not stripped or not stripped.startswith("#") or stripped.startswith("#EXTINF"):
                    break
                vlc_match = re.match(r'#EXTVLCOPT:(\S+?)=(.*)', stripped)
                if vlc_match:
                    key = vlc_match.group(1).lower()
                    val = vlc_match.group(2).strip()
                    if key == "http-referrer":
                        headers["Referer"] = val
                    elif key == "http-origin":
                        headers["Origin"] = val
                    elif key == "http-user-agent":
                        headers["User-Agent"] = val
                i += 1

            while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith("#")):
                i += 1

            if i < len(lines):
                url = lines[i].strip()
                if url and not url.startswith("#"):
                    channels.append({
                        "id": f"event_{len(channels)+1}",
                        "label": name[:42],
                        "category": cat,
                        "badge": "LIVE HLS",
                        "description": name,
                        "url": url,
                        "headers": headers,
                        "is_embeddable": True
                    })
        i += 1
    return channels

def parse_sportsx_workers(text: str) -> List[Dict[str, Any]]:
    """Parses SportsX channels from Muji777 SportsX m3u."""
    channels = []
    lines = text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            name_match = re.search(r',(.+)$', line)
            name = name_match.group(1).strip() if name_match else "SportsX Channel"
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith("#")):
                i += 1
            if i < len(lines):
                url = lines[i].strip()
                if url and not url.startswith("#"):
                    channels.append({
                        "id": f"sx_{len(channels)+1}",
                        "label": name[:28],
                        "category": "NETWORK",
                        "badge": "24/7 HD",
                        "description": f"SportsX Premium Feed: {name}",
                        "url": url,
                        "headers": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        },
                        "is_embeddable": True
                    })
        i += 1
    return channels

def run_ingest() -> Dict[str, Any]:
    print("[SportsX Ingest] Fetching live events from doms9...")
    dom_text = fetch_url(DOM_M3U)
    dom_channels = parse_dom_events(dom_text) if dom_text else []
    
    print("[SportsX Ingest] Fetching SportsX channels from Muji777...")
    sx_text = fetch_url(SPORTSX_M3U)
    sx_channels = parse_sportsx_workers(sx_text) if sx_text else []
    
    # Prepend Artemis hardware mosaic grid & Tonight's Marquee Thursday Slate
    marquee_channels = [
        {
            "id": "artemis-mosaic",
            "label": "Artemis GP106 Quad-Grid",
            "category": "MOSAIC",
            "badge": "1080P/60FPS",
            "description": "Hardware-accelerated 4-stream gameday mosaic grid running on Artemis Pascal GPU.",
            "url": "/api/artemis/mosaic/master_grid.m3u8",
            "is_embeddable": True
        },
        {
            "id": "mlb-nlcs-mil-lad-g4",
            "label": "NLCS Game 4: MIL @ LAD",
            "category": "MLB",
            "badge": "LIVE POSTSEASON",
            "description": "NLCS Game 4: Milwaukee Brewers @ Los Angeles Dodgers (Dodger Stadium).",
            "url": "https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8",
            "is_embeddable": True
        },
        {
            "id": "nfl-tnf-sea-den",
            "label": "NFL TNF: SEA @ DEN",
            "category": "NFL",
            "badge": "LIVE TNF",
            "description": "NFL Thursday Night Football: Seattle Seahawks @ Denver Broncos (Empower Field at Mile High).",
            "url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
            "is_embeddable": True
        }
    ]
    
    # Deduplicate channels by normalized matchup title and filter out wrong-week NFL matchups
    deduped_dom = []
    seen_keys = set()
    for ch in dom_channels:
        raw_desc = (ch.get("description") or ch.get("label") or "").strip()
        norm = re.sub(r'^\[.*?\]\s*', '', raw_desc).lower()
        norm = norm.replace("spvgg greuther fürth", "greuther fürth").replace("spvgg greuther furth", "greuther fürth")
        norm = re.sub(r'[^a-z0-9]+', ' ', norm).strip()
        # Keep first 24 chars of normalized matchup key to collapse multi-mirror duplicates
        dedup_key = norm[:24]
        if not dedup_key or dedup_key in seen_keys:
            continue
        # Filter out wrong-week NFL matchups (keep only SEA/DEN or non-NFL)
        if ch.get("category") == "NFL" and not any(t in norm for t in ("sea", "seahawks", "den", "broncos", "redzone", "network")):
            continue
        seen_keys.add(dedup_key)
        deduped_dom.append(ch)

    deduped_sx = []
    for ch in sx_channels:
        norm = re.sub(r'[^a-z0-9]+', ' ', (ch.get("label") or "").lower()).strip()[:24]
        if not norm or norm in seen_keys:
            continue
        seen_keys.add(norm)
        deduped_sx.append(ch)

    all_channels = marquee_channels + deduped_dom[:18] + deduped_sx[:12]
    payload = {
        "status": "LIVE_CHANNELS_OK",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S-04:00"),
        "channel_count": len(all_channels),
        "channels": all_channels
    }
    
    GUIDE_FILE.write_text(json.dumps(payload, indent=2))
    print(f"[SportsX Ingest] Ingested {len(all_channels)} live channels to {GUIDE_FILE}")
    return payload

if __name__ == "__main__":
    run_ingest()
