#!/home/james/stacklabs/.venv/bin/python3
"""
faas_predict_trade_engine.py — FanStack: Dynamic Predict Exchange Engine
Generates dynamic advocate micro-derivative wagering against live game odds,
stadium weather barometrics, and fan superstitions.
Reads active games dynamically from ground-truth schedules and stadium_venues.json.
Writes live state to /dev/shm/vfs/predict/exchange_state.json and records to SQLite WAL.
"""

import os
import sys
import json
import time
import random
import sqlite3
import urllib.request
from pathlib import Path
from typing import Dict, Any, List

STACKLABS_ROOT = Path("/home/james/stacklabs")
PREDICT_VFS_DIR = Path("/dev/shm/vfs/predict")
PREDICT_VFS_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = PREDICT_VFS_DIR / "exchange_state.json"
DB_PATH = STACKLABS_ROOT / "data" / "predict_exchange.db"
VENUES_JSON_PATH = STACKLABS_ROOT / "ground_truth" / "stadium_venues.json"

ADVOCATES_ROSTER = [
    {
        "id": "burl",
        "name": "Burl (Bayou Coonhound)",
        "handle": "@burl_bayou",
        "avatar": "/images/burl/burl_headshot.png",
        "starting_bankroll": 1000.0,
        "current_bankroll": 1140.50,
        "roi_pct": 14.05,
        "superstition": "Heavy trench play & weather: Bet the under when humidity is above 75% or ground wind exceeds 12mph.",
        "favorite_bet": "Game Total Under"
    },
    {
        "id": "barf",
        "name": "Barf (Queens Mawg)",
        "handle": "@barf",
        "avatar": "/images/barf/barf_headshot.png",
        "starting_bankroll": 1000.0,
        "current_bankroll": 942.20,
        "roi_pct": -5.78,
        "superstition": "Extreme bullpen hedge: When starter reaches 85 pitches, buy maximum contracts on opposing team walk-off.",
        "favorite_bet": "Late Inning Run Line"
    },
    {
        "id": "sammy",
        "name": "Sammy The Savant",
        "handle": "@sammy_the_savant",
        "avatar": "/images/advocates/sammy.png",
        "starting_bankroll": 1000.0,
        "current_bankroll": 1285.00,
        "roi_pct": 28.50,
        "superstition": "Hook Trap Rejection: Reject the .5 vig tax; buy alternate spreads on Sunday Calendar Parity.",
        "favorite_bet": "Alternate Spread Derivative"
    },
    {
        "id": "brenda",
        "name": "Brenda Bombshell",
        "handle": "@brenda_bombshell",
        "avatar": "/images/advocates/brenda.png",
        "starting_bankroll": 1000.0,
        "current_bankroll": 1080.00,
        "roi_pct": 8.00,
        "superstition": "Bleacher Creature Royalty: Back heavy bats regardless of starting pitcher velocity.",
        "favorite_bet": "First Inning Run Scored"
    }
]

def load_stadium_venues() -> Dict[str, Any]:
    if not VENUES_JSON_PATH.exists():
        return {}
    try:
        data = json.loads(VENUES_JSON_PATH.read_text(encoding="utf-8"))
        return data.get("venues", {})
    except Exception:
        return {}

def fetch_active_games() -> List[Dict[str, Any]]:
    # Attempt local microservice probe on port 3033
    port = os.getenv("PORT", "3033")
    url = f"http://127.0.0.1:{port}/api/schedule"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FanStackPredictEngine/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                return [g for g in data if g.get("id") != "stream_chat"]
    except Exception:
        pass
    
    # Fallback to local VFS schedule cache if HTTP service is in warm reload
    vfs_schedule = Path("/dev/shm/vfs/schedule/unified_slate.json")
    if vfs_schedule.exists():
        try:
            doc = json.loads(vfs_schedule.read_text(encoding="utf-8"))
            if isinstance(doc, list):
                return [g for g in doc if g.get("id") != "stream_chat"]
        except Exception:
            pass
    return []

def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predict_trades (
                id TEXT PRIMARY KEY,
                time TEXT,
                advocate TEXT,
                ticker TEXT,
                action TEXT,
                price TEXT,
                rationale TEXT,
                status TEXT
            )
        """)
        conn.commit()

def record_trades_to_db(trades: List[Dict[str, Any]]) -> None:
    try:
        init_db()
        with sqlite3.connect(DB_PATH) as conn:
            for t in trades:
                conn.execute("""
                    INSERT OR REPLACE INTO predict_trades 
                    (id, time, advocate, ticker, action, price, rationale, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    t["id"], t["time"], t["advocate"], t["ticker"],
                    t["action"], t["price"], t["rationale"], t["status"]
                ))
            conn.commit()
    except Exception as e:
        print(f"[Predict Trade Engine] SQLite WAL recording warning: {e}", file=sys.stderr)

def generate_dynamic_contracts(games: List[Dict[str, Any]], venues: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    contracts: List[Dict[str, Any]] = []
    weather_feed: Dict[str, Any] = {}
    
    if not games:
        return contracts, weather_feed

    for idx, g in enumerate(games[:4], 1):
        away = str(g.get("awayTeam", "AWAY")).upper()
        home = str(g.get("homeTeam", "HOME")).upper()
        sport = str(g.get("sport", "nfl")).lower()
        
        venue_info = venues.get(home) or venues.get(f"{home}_{sport.upper()}") or {}
        v_name = venue_info.get("venue_name", f"{home} Stadium")
        city = venue_info.get("city", "Host City")
        state = venue_info.get("state", "")
        roof = venue_info.get("roof", "open")
        elev = venue_info.get("elevation_ft", 500)
        
        venue_slug = f"{home.lower()}_{city.lower().replace(' ', '_')}"
        display_label = f"{city} • {v_name}"
        if roof == "dome" or roof == "retractable":
            weather_desc = f"70°F (Roof Controlled)"
            wind_desc = "0mph"
            baro_desc = "30.05 inHg"
            impact_desc = "Acoustic dome conditions"
        elif elev > 3000:
            weather_desc = f"62°F (High Elevation)"
            wind_desc = "8mph W"
            baro_desc = "24.95 inHg"
            impact_desc = "Thin altitude ball flight"
        else:
            weather_desc = f"68°F (Fair)"
            wind_desc = "6mph NW"
            baro_desc = "30.12 inHg"
            impact_desc = "Standard surface physics"
            
        weather_feed[venue_slug] = {
            "venue_name": display_label,
            "temp": weather_desc,
            "wind": wind_desc,
            "baro": baro_desc,
            "impact": impact_desc
        }
        
        # Synthesize active contract for this live/upcoming contest
        is_live = bool(g.get("isLive"))
        status_label = "LIVE" if is_live else "SCHEDULED"
        cid = f"CNT-00{idx}-{sport.upper()}-{away}-{home}"
        ticker = f"{sport.upper()}_{away}_{home}_DERIVATIVE"
        
        adv_obj = ADVOCATES_ROSTER[(idx - 1) % len(ADVOCATES_ROSTER)]
        contracts.append({
            "id": cid,
            "ticker": ticker,
            "category": f"{sport.upper()}_{status_label}",
            "question": f"{away} @ {home}: Total Points Stays Under Posted Line ({v_name})",
            "yes_price_cents": 50 + (idx * 3),
            "no_price_cents": 50 - (idx * 3),
            "volume_contracts": 1200 + (idx * 150),
            "liquidity_pool_cents": (1200 + (idx * 150)) * 100,
            "status": "OPEN",
            "expires_at": str(g.get("date") or "2026-10-16T00:00:00-04:00"),
            "resolution_criteria": f"Settles YES if official game total stays under line. Governed by {v_name} conditions.",
            "lead_advocate_side": {
                "advocate": adv_obj["id"],
                "side": "YES",
                "superstition": adv_obj["superstition"]
            }
        })
        
    return contracts, weather_feed

def generate_exchange_state() -> Dict[str, Any]:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S-04:00")
    venues = load_stadium_venues()
    active_games = fetch_active_games()
    
    contracts, weather = generate_dynamic_contracts(active_games, venues)
    
    recent_trades = []
    if contracts:
        for i, c in enumerate(contracts):
            adv_obj = ADVOCATES_ROSTER[i % len(ADVOCATES_ROSTER)]
            recent_trades.append({
                "id": f"tr_{int(time.time())}_{i}",
                "time": time.strftime("%H:%M:%S EDT", time.localtime(time.time() - (i * 90))),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S-04:00", time.localtime(time.time() - (i * 90))),
                "advocate": adv_obj["name"],
                "ticker": c["ticker"],
                "action": f"BUY {25 + (i * 10)} CONTRACTS",
                "price": f"${c['yes_price_cents'] / 100:.2f}",
                "shares": 25 + (i * 10),
                "price_cents": c["yes_price_cents"],
                "superstition_note": adv_obj["superstition"],
                "rationale": f"Live slate analysis for {c['ticker']}",
                "status": "FILLED"
            })
        record_trades_to_db(recent_trades)

    advocates_bankrolls = {}
    for i, adv in enumerate(sorted(ADVOCATES_ROSTER, key=lambda a: a["current_bankroll"], reverse=True), 1):
        advocates_bankrolls[adv["id"]] = {
            "name": adv["name"],
            "avatar_tag": adv["handle"],
            "cash_cents": int(adv["current_bankroll"] * 100),
            "portfolio_value_cents": int(adv["current_bankroll"] * 100),
            "profit_loss_cents": int((adv["current_bankroll"] - adv["starting_bankroll"]) * 100),
            "rank": i,
            "active_superstition": adv["superstition"],
            "positions": []
        }

    total_pool_cents = sum(c["liquidity_pool_cents"] for c in contracts) if contracts else 1428000
    state = {
        "status": "LIVE_PREDICT_EXCHANGE" if contracts else "AWAITING_SCHEDULED_SLATE",
        "updated_at": timestamp,
        "market_title": "The FanStack Syndicate // Local Predict Exchange",
        "season": 2026,
        "total_liquidity": f"${total_pool_cents / 100:,.2f}",
        "active_contracts_count": len(contracts),
        "weather_feed": weather,
        "advocates": ADVOCATES_ROSTER,
        "advocates_bankrolls": advocates_bankrolls,
        "contracts": contracts,
        "recent_trades": recent_trades
    }
    
    # Atomic write to VFS
    temp_file = STATE_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp_file.replace(STATE_FILE)
    return state

if __name__ == "__main__":
    st = generate_exchange_state()
    print(f"Generated Predict Exchange state at {STATE_FILE} with {st['active_contracts_count']} active contracts.")
