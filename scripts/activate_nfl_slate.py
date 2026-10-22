#!/usr/bin/env python3
"""
Activate Sunday NFL Slate via FastAPI on Port 8095.
Enforces Invariant I.8 & I.9.
"""

import sys
import json
import urllib.request

API_BASE = "http://127.0.0.1:8095"

def main():
    # 1. Fetch current schedule
    req = urllib.request.Request(f"{API_BASE}/api/now/table/sport_schedule", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    games = data.get("result", [])
    nfl_today = [g for g in games if g.get("sport") == "NFL" and g.get("game_date") == "2026-10-04"]
    print(f"Found {len(nfl_today)} NFL games for 2026-10-04.")

    activated_count = 0
    for g in nfl_today:
        payload = {
            "game_pk": str(g["game_pk"]),
            "sport": "NFL",
            "home_team": g.get("home_team") or "",
            "away_team": g.get("away_team") or "",
            "home_team_name": g.get("home_team_name") or "",
            "away_team_name": g.get("away_team_name") or "",
            "game_date": "2026-10-04",
            "game_time": g.get("game_time") or "1:00 PM",
            "venue": g.get("venue") or "",
            "status": g.get("status") or "Sun, October 4th",
            "room_state": "active",
            "boggs_level": int(g.get("boggs_level") or 3),
            "home_score": int(g.get("home_score") or 0),
            "away_score": int(g.get("away_score") or 0)
        }
        seed_req = urllib.request.Request(
            f"{API_BASE}/api/sports/schedule/seed",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(seed_req, timeout=10) as sresp:
            res = json.loads(sresp.read().decode("utf-8"))
            if res.get("room_state") == "active":
                activated_count += 1
                print(f"[+] Activated {res.get('matchup')} ({res.get('game_pk')})")

    print(f"Total activated: {activated_count}/{len(nfl_today)}")

    # Verification
    vreq = urllib.request.Request(f"{API_BASE}/api/now/table/sport_schedule", headers={"Accept": "application/json"})
    with urllib.request.urlopen(vreq, timeout=10) as vresp:
        vdata = json.loads(vresp.read().decode("utf-8"))
    active_games = [g for g in vdata.get("result", []) if g.get("sport") == "NFL" and g.get("game_date") == "2026-10-04" and g.get("room_state") == "active"]
    print(f"Verified active NFL games: {len(active_games)}")
    assert len(active_games) == 14, f"Expected 14 active NFL games, got {len(active_games)}"
    print("✔ [PASS] 14/14 Sunday NFL rooms active")

if __name__ == "__main__":
    main()
