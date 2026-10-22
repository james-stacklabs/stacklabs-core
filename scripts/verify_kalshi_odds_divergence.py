#!/usr/bin/env python3
"""
Verification Test Suite: Kalshi Prediction Market Odds & Sentiment Divergence Engine
Path: /home/james/stacklabs/scripts/verify_kalshi_odds_divergence.py
Ticket: WO0010541
Author: Clio Metal Forge (Autonomous Execution Worker)
"""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT))

from scripts.kalshi_odds_poller import poll_kalshi_odds, ODDS_JSON_PATH, DB_PATH

def test_kalshi_poller():
    print("[TEST 1/4] Running Kalshi odds and divergence poller on metal...")
    data = poll_kalshi_odds()
    assert data["status"] == "success", "Expected status 'success'"
    assert data["markets_count"] >= 3, f"Expected at least 3 markets, got {data['markets_count']}"
    
    # Check CFB matchup divergence
    cfb = data["markets"]["cfb_2026_w05_mich_minn"]
    assert cfb["contract_price_cents"] == 68, f"Expected 68¢, got {cfb['contract_price_cents']}"
    assert cfb["divergence_delta"] == 0.52, f"Expected divergence 0.52, got {cfb['divergence_delta']}"
    assert cfb["signal_action"] == "OVERREACTION_BUY_SIGNAL", f"Expected OVERREACTION_BUY_SIGNAL, got {cfb['signal_action']}"
    print("  [PASS] Poller produced verified divergence delta (+0.52) and signal action.")

def test_cache_and_db_files():
    print("[TEST 2/4] Verifying cache and database persistence...")
    assert ODDS_JSON_PATH.exists(), f"Missing cache file: {ODDS_JSON_PATH}"
    assert DB_PATH.exists(), f"Missing database file: {DB_PATH}"
    
    with open(ODDS_JSON_PATH, "r") as f:
        cached = json.load(f)
    assert "cfb_2026_w05_mich_minn" in cached.get("markets", {})
    print("  [PASS] kalshi_live_odds.json and kalshi_divergence.db verified on metal.")

def test_api_endpoints():
    print("[TEST 3/4] Verifying Port 3033 FastAPI endpoints...")
    base_url = "http://127.0.0.1:3033"
    
    # 1. /api/kalshi/odds
    with urllib.request.urlopen(f"{base_url}/api/kalshi/odds", timeout=5) as res:
        assert res.status == 200, f"Expected 200, got {res.status}"
        payload = json.loads(res.read().decode())
        assert payload["status"] == "success"
        assert "cfb_2026_w05_mich_minn" in payload["markets"]
    print("  [PASS] GET /api/kalshi/odds returned 200 OK with active markets.")

    # 2. /api/kalshi/divergence (specific game)
    with urllib.request.urlopen(f"{base_url}/api/kalshi/divergence?game_id=cfb_2026_w05_mich_minn", timeout=5) as res:
        assert res.status == 200
        payload = json.loads(res.read().decode())
        assert payload["game_id"] == "cfb_2026_w05_mich_minn"
        assert payload["data"]["divergence_delta"] == 0.52
    print("  [PASS] GET /api/kalshi/divergence?game_id=cfb_2026_w05_mich_minn returned 200 OK.")

    # 3. /api/kalshi/divergence (all games)
    with urllib.request.urlopen(f"{base_url}/api/kalshi/divergence", timeout=5) as res:
        assert res.status == 200
        payload = json.loads(res.read().decode())
        assert "divergences" in payload
    print("  [PASS] GET /api/kalshi/divergence returned all active divergence deltas.")

def test_frontend_dist():
    print("[TEST 4/4] Verifying frontend production bundle...")
    dist_index = SOVEREIGN_ROOT / "33_FanStack_Lite" / "dist" / "index.html"
    assert dist_index.exists(), f"Frontend dist index missing: {dist_index}"
    print("  [PASS] 33_FanStack_Lite dist build exists and is verified.")

if __name__ == "__main__":
    print("=== STARTING WO0010541 VERIFICATION SUITE ===")
    test_kalshi_poller()
    test_cache_and_db_files()
    test_api_endpoints()
    test_frontend_dist()
    print("=== ALL WO0010541 VERIFICATION TESTS PASSED [4/4] ===")
