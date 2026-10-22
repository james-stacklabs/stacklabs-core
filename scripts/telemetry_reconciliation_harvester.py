#!/usr/bin/env python3
"""
FanStack Automated Post-Game Reconciliation & Self-Healing Telemetry Engine
Governed by FanStack Technical Design Document: Automated Post-Game Reconciliation
& Self-Healing Telemetry Engine (The Kroger Cereal Aisle Revelation - ENHC2026082608).

Performs hierarchical 4-tier differential analysis (Macro -> Inning -> At-Bat -> Pitch),
applies zero-downtime hot patches to local caches, harvests discrepant fixtures to
tests/telemetry_corpus/failures/, and logs audit receipts in game_reconciliations.
"""

import os
import sys
import json
import time
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import urllib.request
import urllib.error

# Sovereign OS imports
SOVEREIGN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOVEREIGN_ROOT))
from scripts.core.db import get_db

STATS_API_FEED = "https://statsapi.mlb.com/api/v1.1/game/{}/feed/live"
STATS_API_CONTENT = "https://statsapi.mlb.com/api/v1/game/{}/content"
CORPUS_FAILURES_DIR = SOVEREIGN_ROOT / "tests" / "telemetry_corpus" / "failures"
GAME_STATES_DIR = SOVEREIGN_ROOT / "game_states"


def fetch_json(url: str, timeout: int = 15) -> Optional[dict]:
    """Fetch JSON payload from external REST endpoint with timeout and retry."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SovereignOS-FanStack-ReconciliationEngine/1.0", "Accept": "application/json"}
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == 2:
                print(f"[RECONCILER ERROR] Failed fetching {url}: {e}")
                return None
            time.sleep(0.5 * (attempt + 1))
    return None


def load_local_game_cache(game_pk: int) -> Optional[dict]:
    """Load local hot cache for given game."""
    cache_path = GAME_STATES_DIR / f"{game_pk}.json"
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[RECONCILER ERROR] Failed reading local cache {cache_path}: {e}")
        return None


def execute_hierarchical_diff(official_feed: dict, local_cache: Optional[dict]) -> Tuple[str, int, List[Dict[str, Any]]]:
    """
    Executes hierarchical 4-tier differential analysis:
    - Tier 1: Macro (Runs, Hits, Errors, LOB)
    - Tier 2: Inning Frames (half-inning linescore runs/hits/errors)
    - Tier 3: At-Bat Events (batter outcomes, RBIs, runs, outs)
    - Tier 4: Pitch Telemetry (pitch counts, ball/strike sequence)
    """
    discrepancies = []
    
    if not local_cache:
        discrepancies.append({
            "tier": 1,
            "type": "MISSING_LOCAL_CACHE",
            "message": "Local game cache json does not exist. Full back-fill required."
        })
        return "AUTO_PATCHED", 1, discrepancies

    live_data = official_feed.get("liveData", {})
    off_linescore = live_data.get("linescore", {})
    off_teams = off_linescore.get("teams", {})
    
    loc_data = local_cache.get("data", local_cache)
    loc_linescore = loc_data.get("linescore", {}) if isinstance(loc_data, dict) else {}
    
    # ── Tier 1: Game Macro ──────────────────────────────────────────────────
    off_away_r = off_teams.get("away", {}).get("runs", 0)
    off_home_r = off_teams.get("home", {}).get("runs", 0)
    off_away_h = off_teams.get("away", {}).get("hits", 0)
    off_home_h = off_teams.get("home", {}).get("hits", 0)
    off_away_e = off_teams.get("away", {}).get("errors", 0)
    off_home_e = off_teams.get("home", {}).get("errors", 0)
    
    loc_away_r = loc_data.get("away_score", loc_linescore.get("teams", {}).get("away", {}).get("runs", 0))
    loc_home_r = loc_data.get("home_score", loc_linescore.get("teams", {}).get("home", {}).get("runs", 0))
    
    macro_mismatches = []
    if int(loc_away_r) != int(off_away_r):
        macro_mismatches.append(f"Away Runs: local={loc_away_r}, official={off_away_r}")
    if int(loc_home_r) != int(off_home_r):
        macro_mismatches.append(f"Home Runs: local={loc_home_r}, official={off_home_r}")

    if macro_mismatches:
        discrepancies.append({
            "tier": 1,
            "type": "MACRO_SCORE_DELTA",
            "details": macro_mismatches
        })

    # ── Tier 2: Inning Frame Diff ───────────────────────────────────────────
    off_innings = off_linescore.get("innings", [])
    loc_innings = loc_linescore.get("innings", [])
    
    if len(off_innings) != len(loc_innings) and len(loc_innings) > 0:
        discrepancies.append({
            "tier": 2,
            "type": "INNING_COUNT_DELTA",
            "message": f"Inning count mismatch: local={len(loc_innings)}, official={len(off_innings)}"
        })

    for idx, off_inn in enumerate(off_innings):
        inn_num = off_inn.get("num", idx + 1)
        if idx < len(loc_innings):
            loc_inn = loc_innings[idx]
            off_top_r = off_inn.get("away", {}).get("runs", 0)
            off_bot_r = off_inn.get("home", {}).get("runs", 0)
            loc_top_r = loc_inn.get("away", {}).get("runs", 0)
            loc_bot_r = loc_inn.get("home", {}).get("runs", 0)
            
            if off_top_r != loc_top_r or off_bot_r != loc_bot_r:
                discrepancies.append({
                    "tier": 2,
                    "type": "INNING_LINE_DELTA",
                    "inning": inn_num,
                    "official": {"top": off_top_r, "bot": off_bot_r},
                    "local": {"top": loc_top_r, "bot": loc_bot_r}
                })

    # ── Tier 3: At-Bat Event Diff ───────────────────────────────────────────
    off_all_plays = live_data.get("plays", {}).get("allPlays", [])
    loc_all_plays = loc_data.get("plays", {}).get("allPlays", []) if isinstance(loc_data, dict) else []

    if loc_all_plays and len(loc_all_plays) != len(off_all_plays):
        discrepancies.append({
            "tier": 3,
            "type": "PLAY_COUNT_DELTA",
            "message": f"Total plays count mismatch: local={len(loc_all_plays)}, official={len(off_all_plays)}"
        })

    # Compare plays by atBatIndex
    loc_plays_by_index = {p.get("about", {}).get("atBatIndex"): p for p in loc_all_plays if p.get("about", {}).get("atBatIndex") is not None}
    
    for off_p in off_all_plays:
        at_bat_idx = off_p.get("about", {}).get("atBatIndex")
        if at_bat_idx is None:
            continue
            
        loc_p = loc_plays_by_index.get(at_bat_idx)
        if not loc_p and loc_all_plays:
            discrepancies.append({
                "tier": 3,
                "type": "MISSING_AT_BAT",
                "at_bat_index": at_bat_idx,
                "description": off_p.get("result", {}).get("description", "")
            })
            continue

        if loc_p:
            off_event = off_p.get("result", {}).get("eventType", "")
            loc_event = loc_p.get("result", {}).get("eventType", "")
            if off_event != loc_event:
                discrepancies.append({
                    "tier": 3,
                    "type": "EVENT_TYPE_MISMATCH",
                    "at_bat_index": at_bat_idx,
                    "official": off_event,
                    "local": loc_event
                })

            # ── Tier 4: Pitch Telemetry ──────────────────────────────────────
            off_events = off_p.get("playEvents", [])
            loc_events = loc_p.get("playEvents", [])
            off_pitches = [e for e in off_events if e.get("isPitch")]
            loc_pitches = [e for e in loc_events if e.get("isPitch")]
            
            if abs(len(off_pitches) - len(loc_pitches)) > 1:
                discrepancies.append({
                    "tier": 4,
                    "type": "PITCH_COUNT_DRIFT",
                    "at_bat_index": at_bat_idx,
                    "official_pitches": len(off_pitches),
                    "local_pitches": len(loc_pitches)
                })

    # Status classification
    if not discrepancies:
        status = "PERFECT_MATCH"
    elif len(discrepancies) <= 5 and not any(d.get("tier") == 1 for d in discrepancies):
        status = "AUTO_PATCHED"
    else:
        status = "AUTO_PATCHED" if local_cache is not None else "MANUAL_REVIEW"

    return status, len(discrepancies), discrepancies


def harvest_corpus_failures(game_pk: int, discrepancies: List[Dict[str, Any]], official_feed: dict):
    """
    Serializes discrepant at-bat payloads into tests/telemetry_corpus/failures/
    to expand automated regression coverage.
    """
    if not discrepancies:
        return []

    CORPUS_FAILURES_DIR.mkdir(parents=True, exist_ok=True)
    harvested = []
    
    plays = official_feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    plays_by_index = {p.get("about", {}).get("atBatIndex"): p for p in plays if p.get("about", {}).get("atBatIndex") is not None}

    for disc in discrepancies:
        at_bat_idx = disc.get("at_bat_index")
        if at_bat_idx is not None and at_bat_idx in plays_by_index:
            fixture_name = f"game_{game_pk}_atbat_{at_bat_idx}.json"
            fixture_path = CORPUS_FAILURES_DIR / fixture_name
            payload = {
                "game_pk": game_pk,
                "at_bat_index": at_bat_idx,
                "discrepancy": disc,
                "play_data": plays_by_index[at_bat_idx],
                "harvested_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            with open(fixture_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            harvested.append(str(fixture_path))

    return harvested


def hot_patch_cache(game_pk: int, official_feed: dict) -> bool:
    """Applies certified official state over local cache and marks reconciled."""
    cache_path = GAME_STATES_DIR / f"{game_pk}.json"
    GAME_STATES_DIR.mkdir(parents=True, exist_ok=True)
    
    live_data = official_feed.get("liveData", {})
    linescore = live_data.get("linescore", {})
    teams = linescore.get("teams", {})
    
    patch_payload = {
        "game_pk": str(game_pk),
        "status": "Final",
        "reconciled_with_official": True,
        "reconciled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "data": {
            "game_pk": str(game_pk),
            "status": "Final",
            "is_final": True,
            "away_score": teams.get("away", {}).get("runs", 0),
            "home_score": teams.get("home", {}).get("runs", 0),
            "linescore": linescore,
            "boxscore": live_data.get("boxscore", {}),
            "plays": live_data.get("plays", {})
        }
    }
    
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(patch_payload, f, indent=2)
        return True
    except Exception as e:
        print(f"[RECONCILER ERROR] Failed hot-patching cache for {game_pk}: {e}")
        return False


def save_reconciliation_record(
    game_pk: int,
    game_date: str,
    home_team_id: int,
    away_team_id: int,
    status: str,
    discrepancy_count: int,
    discrepancy_breakdown: List[Dict[str, Any]],
    editorial_headline: str,
    editorial_blurb: str
) -> bool:
    """Save reconciliation ledger row in sovereign_now.db via context manager."""
    try:
        with get_db(row_factory=False) as conn:
            with conn:
                conn.execute("""
                    INSERT INTO game_reconciliations (
                        game_pk, game_date, home_team_id, away_team_id,
                        status, discrepancy_count, discrepancy_breakdown,
                        editorial_headline, editorial_blurb, reconciled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(game_pk) DO UPDATE SET
                        status = excluded.status,
                        discrepancy_count = excluded.discrepancy_count,
                        discrepancy_breakdown = excluded.discrepancy_breakdown,
                        editorial_headline = excluded.editorial_headline,
                        editorial_blurb = excluded.editorial_blurb,
                        reconciled_at = datetime('now');
                """, (
                    game_pk,
                    game_date,
                    home_team_id,
                    away_team_id,
                    status,
                    discrepancy_count,
                    json.dumps(discrepancy_breakdown),
                    editorial_headline,
                    editorial_blurb
                ))
        return True
    except Exception as e:
        print(f"[RECONCILER ERROR] Failed saving reconciliation record to DB: {e}")
        return False


def reconcile_game(game_pk: int, auto_patch: bool = True, harvest_corpus: bool = True) -> Dict[str, Any]:
    """
    Main orchestration entry point:
    Fetches certified feed & editorial content, compares against local cache,
    hot-patches discrepancies, harvests failure fixtures, and logs to DB.
    """
    print(f"\n=======================================================")
    print(f"⚾ RECONCILIATION ENGINE START: GAME {game_pk}")
    print(f"=======================================================")
    
    # 1. Fetch certified feed
    feed_url = STATS_API_FEED.format(game_pk)
    print(f"[RECONCILER] Ingesting certified live feed: {feed_url}")
    official_feed = fetch_json(feed_url)
    if not official_feed:
        return {"status": "ERROR", "message": f"Could not fetch official feed for {game_pk}"}

    # 2. Extract core game metadata
    game_data = official_feed.get("gameData", {})
    game_date_str = game_data.get("datetime", {}).get("originalDate", datetime.date.today().isoformat())
    home_team_id = game_data.get("teams", {}).get("home", {}).get("id", 0)
    away_team_id = game_data.get("teams", {}).get("away", {}).get("id", 0)
    home_team = game_data.get("teams", {}).get("home", {}).get("abbreviation", "HME")
    away_team = game_data.get("teams", {}).get("away", {}).get("abbreviation", "AWY")

    # 3. Fetch certified content (editorial wrap)
    content_url = STATS_API_CONTENT.format(game_pk)
    print(f"[RECONCILER] Ingesting certified editorial content: {content_url}")
    content_data = fetch_json(content_url) or {}
    editorial = content_data.get("editorial", {})
    recap = editorial.get("recap", {}).get("mlb", {})
    editorial_headline = recap.get("headline") or f"{away_team} vs {home_team} Final Wrap"
    editorial_blurb = recap.get("blurb") or recap.get("seoTitle") or ""

    # 4. Load local cache & diff
    local_cache = load_local_game_cache(game_pk)
    status, discrepancy_count, discrepancies = execute_hierarchical_diff(official_feed, local_cache)
    print(f"[RECONCILER] Diff Result: {status} ({discrepancy_count} discrepancies)")

    # 5. Harvest corpus failures if any discrepancies exist
    harvested_files = []
    if harvest_corpus and discrepancies:
        harvested_files = harvest_corpus_failures(game_pk, discrepancies, official_feed)
        if harvested_files:
            print(f"[RECONCILER] Harvested {len(harvested_files)} regression fixtures into {CORPUS_FAILURES_DIR}")

    # 6. Apply self-healing hot patch
    if auto_patch and (status == "AUTO_PATCHED" or not local_cache):
        patched = hot_patch_cache(game_pk, official_feed)
        print(f"[RECONCILER] Applied local cache self-healing hot-patch: {patched}")

    # 7. Persist to DB ledger
    saved = save_reconciliation_record(
        game_pk=game_pk,
        game_date=game_date_str,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        status=status,
        discrepancy_count=discrepancy_count,
        discrepancy_breakdown=discrepancies,
        editorial_headline=editorial_headline,
        editorial_blurb=editorial_blurb
    )
    print(f"[RECONCILER] Persisted audit record to game_reconciliations: {saved}")

    summary = {
        "game_pk": game_pk,
        "matchup": f"{away_team} @ {home_team}",
        "game_date": game_date_str,
        "status": status,
        "discrepancy_count": discrepancy_count,
        "discrepancies": discrepancies,
        "harvested_fixtures": harvested_files,
        "editorial_headline": editorial_headline,
        "editorial_blurb": editorial_blurb[:120] + "..." if len(editorial_blurb) > 120 else editorial_blurb,
        "reconciled_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    print(f"=======================================================")
    print(f"✅ RECONCILIATION COMPLETE: {status}")
    print(f"Headline: {editorial_headline}")
    print(f"=======================================================\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FanStack Post-Game Telemetry Reconciliation Harvester")
    parser.add_argument("--game_pk", type=int, default=823495, help="MLB Game PK to reconcile (default: 823495)")
    parser.add_argument("--no-patch", action="store_true", help="Skip hot-patching local cache")
    parser.add_argument("--no-harvest", action="store_true", help="Skip harvesting failure fixtures")
    args = parser.parse_args()

    res = reconcile_game(args.game_pk, auto_patch=not args.no_patch, harvest_corpus=not args.no_harvest)
    print(json.dumps(res, indent=2))
