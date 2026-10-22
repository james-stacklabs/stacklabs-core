#!/usr/bin/env python3
"""
StackLabs Sovereign OS: Sports Ground Truth Ingestion Daemon
Path: /home/james/stacklabs/scripts/sync_sports_ground_truth.py

Pulls deterministic, unauthenticated edge REST telemetry from:
1. MLB StatsAPI (Transactions, Postseason Schedules, Rosters)
2. ESPN Site Core APIs (NFL/CFB News, Roster Depth, Live Scores)
3. National Weather Service (Stadium Environmental Telemetry)

Executes atomic_commit via ground_truth_daemon with SHA-256 zero-write caching.
"""

import os
import sys
import json
import hashlib
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Enforce project path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ground_truth_daemon import (
    VAULT_DIR,
    SportsGroundTruth,
    atomic_commit
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("sports_sync")

TARGET_LEDGER = VAULT_DIR / "sports_ground_truth.json"
USER_AGENT = "StackLabs-Sovereign-GroundTruth/1.0 (james@stacklabsllc.com)"


def fetch_json(url: str, timeout: float = 8.0) -> dict:
    """Fetch JSON from unauthenticated HTTP endpoint with proper User-Agent."""
    ua = USER_AGENT
    if "espn.com" in url:
        ua = "StackLabs-Sovereign-GroundTruth/1.0"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning(f"[FETCH-FAIL] {url} -> {e}")
    return {}


def get_current_dates():
    """Return today and yesterday in YYYY-MM-DD format (EDT/UTC aligned)."""
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return today, yesterday


def fetch_mlb_transactions(start_date: str, end_date: str) -> list:
    """Pull official MLB transactions from Fastly Edge CDN."""
    url = f"https://statsapi.mlb.com/api/v1/transactions?startDate={start_date}&endDate={end_date}"
    data = fetch_json(url)
    transactions = []
    for item in data.get("transactions", []):
        transactions.append({
            "id": item.get("id"),
            "date": item.get("date"),
            "type": item.get("type", {}).get("description", "Unknown"),
            "description": item.get("description", ""),
            "player": item.get("person", {}).get("fullName", ""),
            "from_team": item.get("fromTeam", {}).get("name", ""),
            "to_team": item.get("toTeam", {}).get("name", "")
        })
    return transactions


def fetch_mlb_postseason_schedule(date_str: str) -> list:
    """Pull live MLB schedule linescores and series status."""
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}&hydrate=linescore,decisions,seriesStatus"
    data = fetch_json(url)
    games = []
    for date_item in data.get("dates", []):
        for g in date_item.get("games", []):
            teams = g.get("teams", {})
            away = teams.get("away", {})
            home = teams.get("home", {})
            linescore = g.get("linescore", {})
            games.append({
                "game_pk": g.get("gamePk"),
                "status": g.get("status", {}).get("detailedState", ""),
                "series_description": g.get("seriesDescription", ""),
                "away_team": away.get("team", {}).get("name", ""),
                "away_score": away.get("score", 0),
                "home_team": home.get("team", {}).get("name", ""),
                "home_score": home.get("score", 0),
                "current_inning": linescore.get("currentInningOrdinal", ""),
                "is_top_inning": linescore.get("isTopInning", False)
            })
    return games


def fetch_nfl_news_wire() -> list:
    """Pull ESPN NFL news feed for transactions, trade confirmations, and injury alerts."""
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news"
    data = fetch_json(url)
    news = []
    for article in data.get("articles", [])[:15]:
        news.append({
            "headline": article.get("headline", ""),
            "description": article.get("description", ""),
            "published": article.get("published", ""),
            "type": article.get("type", "")
        })
    return news


def fetch_stadium_weather(lat: float, lon: float) -> dict:
    """Query National Weather Service for point coordinates."""
    url = f"https://api.weather.gov/points/{lat},{lon}"
    data = fetch_json(url)
    forecast_url = data.get("properties", {}).get("forecastHourly")
    if not forecast_url:
        return {}
    
    forecast_data = fetch_json(forecast_url)
    periods = forecast_data.get("properties", {}).get("periods", [])
    if not periods:
        return {}

    current = periods[0]
    return {
        "temperature_f": current.get("temperature"),
        "wind_speed": current.get("windSpeed"),
        "wind_direction": current.get("windDirection"),
        "short_forecast": current.get("shortForecast"),
        "timestamp": current.get("startTime")
    }


def sync_all():
    """Main ingestion coordinator."""
    if not TARGET_LEDGER.exists():
        logger.error(f"Target ledger not found: {TARGET_LEDGER}")
        return False

    with open(TARGET_LEDGER, "r", encoding="utf-8") as f:
        current_data = json.load(f)

    today_str, yesterday_str = get_current_dates()
    logger.info(f"[SYNC-START] Ingesting sports ground truth for {today_str}...")

    # 1. MLB Transactions (Today & Yesterday)
    mlb_txs = fetch_mlb_transactions(yesterday_str, today_str)
    if mlb_txs:
        current_data.setdefault("daily_transactions", {})["mlb"] = mlb_txs[:20]
        logger.info(f"  -> Captured {len(mlb_txs)} MLB transactions.")

    # 2. MLB Postseason Live Slate
    mlb_slate = fetch_mlb_postseason_schedule(today_str)
    if mlb_slate:
        current_data.setdefault("live_game_slate", {})["mlb"] = mlb_slate
        logger.info(f"  -> Captured {len(mlb_slate)} MLB postseason games.")

    # 3. NFL News & Transaction Wire
    nfl_news = fetch_nfl_news_wire()
    if nfl_news:
        current_data.setdefault("daily_transactions", {})["nfl_news"] = nfl_news
        logger.info(f"  -> Captured {len(nfl_news)} NFL news wire items.")

    # 4. Stadium Environmental Nodes (Sample: Truist Park & MetLife)
    stadium_coords = {
        "truist_park": (33.8908, -84.4678),
        "metlife_stadium": (40.8135, -74.0745)
    }
    weather_updates = {}
    for st_name, (lat, lon) in stadium_coords.items():
        w = fetch_stadium_weather(lat, lon)
        if w:
            weather_updates[st_name] = w
    if weather_updates:
        current_data.setdefault("stadium_weather_nodes", {}).update(weather_updates)
        logger.info(f"  -> Updated {len(weather_updates)} stadium weather nodes.")

    # Check if payload changed before updating updated_at to preserve zero-cycle SHA-256 caching
    target_existing_bytes = TARGET_LEDGER.read_bytes()
    test_json = json.dumps(current_data, indent=2, sort_keys=True) + "\n"
    if hashlib.sha256(test_json.encode("utf-8")).hexdigest() == hashlib.sha256(target_existing_bytes).hexdigest():
        logger.info("[NO-CHANGE] SHA256 match. 0 NVMe write cycles burned.")
        logger.info("[SYNC-FINISH] Result: NO_CHANGE (success=False)")
        return False

    # Update metadata timestamp on legitimate delta
    current_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Commit via atomic ground truth daemon (burns 0 write cycles if SHA matches)
    success, reason = atomic_commit(
        file_path=TARGET_LEDGER,
        new_data=current_data,
        model_cls=SportsGroundTruth,
        sync_drive=True
    )
    logger.info(f"[SYNC-FINISH] Result: {reason} (success={success})")
    return success


if __name__ == "__main__":
    sync_all()
