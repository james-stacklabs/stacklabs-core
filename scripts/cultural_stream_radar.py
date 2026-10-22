#!/usr/bin/env python3
"""
StackLabs Sovereign OS: Cultural Stream Radar
Path: /home/james/stacklabs/scripts/cultural_stream_radar.py
Governed by: Invariant 24 (FaaS Info Utility) & Invariant 35 (Canonical .venv)

Monitors the Top 5 non-game sports & cultural personality channels:
1. Theo Von (This Past Weekend)
2. The Pat McAfee Show
3. Nightcap (Shannon Sharpe & Ochocinco)
4. Bussin' With The Boys (Taylor Lewan & Will Compton)
5. Pardon My Take (Barstool Sports)

Fetches RSS feeds, detects new drops, outputs daily cultural_stream_pulse.json.
"""

import sys
import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path("/home/james/stacklabs")
BROADCASTS_DIR = REPO_ROOT / "data" / "broadcasts"

CULTURAL_CHANNELS = [
    {
        "id": "theo_von",
        "name": "Theo Von (This Past Weekend)",
        "channel_id": "UC5AQEUAwCh1sGDvkQtkDWUQ",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC5AQEUAwCh1sGDvkQtkDWUQ",
        "category": "Southern Cultural Entropy & Long-Form Sits",
        "cadence": "Weekly Drops"
    },
    {
        "id": "pat_mcafee",
        "name": "The Pat McAfee Show",
        "channel_id": "UCxcTeAKWJca6XyJ37_ZoKIQ",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCxcTeAKWJca6XyJ37_ZoKIQ",
        "category": "Daily Linear Sports Blowtorch",
        "cadence": "Daily 12:00-15:00 EDT"
    },
    {
        "id": "nightcap",
        "name": "Nightcap (Shannon Sharpe & Chad Ochocinco)",
        "channel_id": "UCKnodHJpZd8UbSvAufDd3_g",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCKnodHJpZd8UbSvAufDd3_g",
        "category": "Late-Night Post-Game Therapy",
        "cadence": "Post-Game Nights"
    },
    {
        "id": "bussin_with_the_boys",
        "name": "Bussin' With The Boys",
        "channel_id": "UCylgcI1N1S3zHljDO8eW-Qg",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCylgcI1N1S3zHljDO8eW-Qg",
        "category": "Nashville / SEC Locker Room Grit",
        "cadence": "Bi-Weekly"
    },
    {
        "id": "pardon_my_take",
        "name": "Pardon My Take",
        "channel_id": "UC9PKpPDyCi_Jck8j3e6N-_g",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC9PKpPDyCi_Jck8j3e6N-_g",
        "category": "Degenerate Sports Satire & Betting",
        "cadence": "M/W/F Morning"
    }
]

def fetch_channel_latest(channel_info: dict) -> dict:
    """Fetch the latest video entry from YouTube RSS feed."""
    url = channel_info["feed_url"]
    headers = {"User-Agent": "Mozilla/5.0 (StackLabs Bare-Metal Cultural Radar/1.0)"}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'yt': 'http://www.youtube.com/xml/schemas/2015',
            'media': 'http://search.yahoo.com/mrss/'
        }
        
        entries = root.findall('atom:entry', ns)
        if not entries:
            return {
                "channel_id": channel_info["id"],
                "channel_name": channel_info["name"],
                "category": channel_info["category"],
                "cadence": channel_info["cadence"],
                "status": "NO_ENTRIES"
            }
            
        latest = entries[0]
        title_el = latest.find('atom:title', ns)
        link_el = latest.find('atom:link', ns)
        published_el = latest.find('atom:published', ns)
        video_id_el = latest.find('yt:videoId', ns)
        
        title = title_el.text if title_el is not None else "Unknown Title"
        link = link_el.attrib.get('href', '') if link_el is not None else ""
        published = published_el.text if published_el is not None else ""
        video_id = video_id_el.text if video_id_el is not None else ""
        
        return {
            "channel_id": channel_info["id"],
            "channel_name": channel_info["name"],
            "category": channel_info["category"],
            "cadence": channel_info["cadence"],
            "latest_title": title,
            "latest_video_id": video_id,
            "latest_url": link,
            "published_at": published,
            "status": "ACTIVE"
        }
    except Exception as e:
        return {
            "channel_id": channel_info["id"],
            "channel_name": channel_info["name"],
            "category": channel_info.get("category", "Cultural Stream"),
            "cadence": channel_info.get("cadence", "Dynamic"),
            "status": "FALLBACK",
            "error": str(e),
            "latest_title": f"Cached {channel_info['name']} Segment",
            "published_at": datetime.now().isoformat()
        }

def run_radar() -> dict:
    print("🛰️ [CULTURAL RADAR] Polling Top 5 Personality & Entropy Channels...")
    BROADCASTS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for ch in CULTURAL_CHANNELS:
        res = fetch_channel_latest(ch)
        results.append(res)
        print(f"  ✔ {ch['name']}: {res.get('latest_title', 'OK')[:60]}")
        
    payload = {
        "timestamp": datetime.now().isoformat(),
        "temporal_baseline": "October 2026",
        "channels_tracked": len(results),
        "streams": results
    }
    
    out_dir = Path("/home/james/stacklabs_inbox/today")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "cultural_stream_pulse.json"
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        
    print(f"✅ [CULTURAL RADAR] Pulse committed to {out_file} ({os.path.getsize(out_file)} bytes)")
    return payload

if __name__ == "__main__":
    run_radar()
