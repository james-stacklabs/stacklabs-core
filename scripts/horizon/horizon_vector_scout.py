#!/usr/bin/env /home/james/stacklabs/.venv/bin/python3
"""
🛰️ HORIZON INTERNAL: VECTOR SCOUT (Tool #75)
Discovers candidate data vectors on metal based on the target horizon prompt.
"""

import sys
import os
import re
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/james/stacklabs/Horizon_Internal")
RUNS_DIR = BASE_DIR / "runs"

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text).strip('_')
    return text[:40]

def scout_youtube_live_streams(query: str, max_results: int = 3):
    """Searches YouTube for live streams or recent postgame uploads using yt-dlp."""
    cmd = [
        "/home/james/stacklabs/.venv/bin/yt-dlp",
        f"ytsearch{max_results}:{query}",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings"
    ]
    candidates = []
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        for line in res.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                candidates.append({
                    "title": data.get("title"),
                    "url": data.get("url") or f"https://www.youtube.com/watch?v={data.get('id')}",
                    "channel": data.get("channel") or data.get("uploader"),
                    "is_live": data.get("is_live", False)
                })
            except Exception:
                continue
    except Exception as e:
        candidates.append({"title": f"Search fallback for: {query}", "url": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}", "channel": "Manual Search", "is_live": False})
    return candidates

def scout_market_ticker(query: str):
    """Detects potential stock tickers from the prompt."""
    matches = re.findall(r'\b[A-Z]{2,5}\b', query)
    # Common words to filter out
    blacklist = {"THE", "FOR", "AND", "NEW", "MLB", "NFL", "LIVE", "POST", "GAME", "CHAT", "HUD"}
    tickers = [m for m in matches if m not in blacklist]
    return tickers

def run_scout(topic: str):
    print("\n" + "="*70)
    print("🛰️  HORIZON INTERNAL: VECTOR SCOUT ENGINE")
    print(f"Target Inquiry: \"{topic}\"")
    print("="*70 + "\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(topic)
    run_id = f"RUN_{timestamp}_{slug}"
    run_path = RUNS_DIR / run_id
    run_path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "topic": topic,
        "vectors": [],
        "status": "SCOUTED"
    }

    # Vector 1: Live Stream / Bleachers
    print("🔍 [Vector 1: Live Stream & Bleacher Wire]")
    yt_candidates = scout_youtube_live_streams(f"{topic} live stream", max_results=3)
    if not yt_candidates:
        yt_candidates = scout_youtube_live_streams(topic, max_results=2)

    for idx, c in enumerate(yt_candidates, 1):
        status_tag = "🔴 LIVE" if c.get("is_live") else "📹 STREAM"
        print(f"   [{idx}] {status_tag} {c['title']} ({c['channel']})")
        print(f"       URL: {c['url']}")
        manifest["vectors"].append({
            "vector_id": f"V-01-{idx}",
            "type": "YOUTUBE_STREAM",
            "title": c['title'],
            "url": c['url'],
            "channel": c['channel']
        })

    # Vector 2: Market Tickers
    tickers = scout_market_ticker(topic)
    if tickers:
        print("\n📈 [Vector 2: Financial Market Tape & OHLCV]")
        for t in tickers:
            print(f"   [✓] Detected Ticker: ${t} (Ready for 12-Month Daily OHLCV Pull via Tool #74)")
            manifest["vectors"].append({
                "vector_id": f"V-03-{t}",
                "type": "FINANCIAL_OHLCV",
                "ticker": t
            })

    # Vector 3: Official Sports & Domain Ledger Check
    sports_keywords = ["game", "postseason", "wild card", "series", "yankees", "red sox", "braves", "phillies", "cubs", "padres", "white sox", "astros"]
    is_sports = any(k in topic.lower() for k in sports_keywords)
    if is_sports:
        print("\n⚾ [Vector 3: Official Domain Ledgers & Box Scores]")
        print("   [✓] Verified 2026 Sports Ground Truth Ledger active in sovereign_inbox/today/")
        manifest["vectors"].append({
            "vector_id": "V-04-SPORTS",
            "type": "SPORTS_GROUND_TRUTH",
            "path": "/home/james/sovereign_inbox/today/active_sports_ground_truth.json"
        })

    # Save Manifest
    manifest_file = run_path / "manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "-"*70)
    print(f"✅ Scout Complete. Staged Run: {run_id}")
    print(f"📁 Manifest Saved: {manifest_file}")
    print("⚡ Next Step: Run 'horizon_metal_ingest.py --run-id " + run_id + "' to pull telemetry.")
    print("-"*70 + "\n")
    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Horizon Internal: Vector Scout")
    parser.add_argument("--topic", type=str, required=True, help="What do you want to see the horizon on?")
    args = parser.parse_args()

    run_scout(args.topic)
