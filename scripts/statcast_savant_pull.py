#!/usr/bin/env python3
"""
Baseball Savant Statcast Puller & Backfill Engine
Path: /home/james/stacklabs/scripts/statcast_savant_pull.py

Pulls pitch-by-pitch Statcast telemetry from Baseball Savant (with real-time
MLB Stats API v1.1 Statcast live feed fallback when Savant's CSV index lags on
same-day / rescheduled games) into /home/james/stacklabs/data/sovereign_intelligence.db.
Supports on-demand backfill for missed or rescheduled games.
"""

import os
import sys
import argparse
import sqlite3
import requests
import pandas as pd
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

DB_PATH = Path("/home/james/stacklabs/data/sovereign_intelligence.db")
TABLE_NAME = "statcast_pitches"

STATCAST_DDL = """
CREATE TABLE IF NOT EXISTS statcast_pitches (
    pitch_type TEXT,
    game_date TEXT,
    release_speed REAL,
    release_pos_x REAL,
    release_pos_z REAL,
    player_name TEXT,
    batter INTEGER,
    pitcher INTEGER,
    events TEXT,
    description TEXT,
    spin_dir REAL,
    zone INTEGER,
    des TEXT,
    game_type TEXT,
    stand TEXT,
    p_throws TEXT,
    home_team TEXT,
    away_team TEXT,
    type TEXT,
    hit_location INTEGER,
    bb_type TEXT,
    balls INTEGER,
    strikes INTEGER,
    game_year INTEGER,
    pfx_x REAL,
    pfx_z REAL,
    plate_x REAL,
    plate_z REAL,
    on_3b INTEGER,
    on_2b INTEGER,
    on_1b INTEGER,
    outs_when_up INTEGER,
    inning INTEGER,
    inning_topbot TEXT,
    launch_speed REAL,
    launch_angle REAL,
    effective_speed REAL,
    release_spin_rate REAL,
    release_extension REAL,
    game_pk INTEGER,
    pitcher_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

TEAM_ABBR = {
    'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL',
    'Baltimore Orioles': 'BAL',    'Boston Red Sox': 'BOS',
    'Chicago Cubs': 'CHC',         'Chicago White Sox': 'CWS',
    'Cincinnati Reds': 'CIN',      'Cleveland Guardians': 'CLE',
    'Colorado Rockies': 'COL',     'Detroit Tigers': 'DET',
    'Houston Astros': 'HOU',       'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA',   'Los Angeles Dodgers': 'LAD',
    'Miami Marlins': 'MIA',        'Milwaukee Brewers': 'MIL',
    'Minnesota Twins': 'MIN',      'New York Mets': 'NYM',
    'New York Yankees': 'NYY',     'Oakland Athletics': 'OAK',
    'Philadelphia Phillies': 'PHI','Pittsburgh Pirates': 'PIT',
    'San Diego Padres': 'SD',      'San Francisco Giants': 'SF',
    'Seattle Mariners': 'SEA',     'St. Louis Cardinals': 'STL',
    'Tampa Bay Rays': 'TB',        'Texas Rangers': 'TEX',
    'Toronto Blue Jays': 'TOR',    'Washington Nationals': 'WSH',
    'Athletics': 'OAK',
}


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(STATCAST_DDL)
    conn.commit()
    conn.close()


def fetch_live_statcast_fallback(start_date: str, end_date: str, team: str = None) -> pd.DataFrame:
    """Fallback to MLB Stats API v1.1 live feed for same-day / newly completed games not yet indexed in Savant CSV."""
    sched_url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "startDate": start_date,
        "endDate": end_date,
        "gameType": "R,F,D,L,W,P",
    }
    res = requests.get(sched_url, params=params, timeout=20).json()
    rows = []
    for dblock in res.get("dates", []):
        gdate = dblock.get("date", start_date)
        gyear = int(gdate[:4]) if len(gdate) >= 4 else 2026
        for g in dblock.get("games", []):
            gpk = int(g.get("gamePk", 0))
            gtype = g.get("gameType", "R")
            teams = g.get("teams", {})
            hname = teams.get("home", {}).get("team", {}).get("name", "")
            aname = teams.get("away", {}).get("team", {}).get("name", "")
            habbr = TEAM_ABBR.get(hname, hname[:3].upper())
            aabbr = TEAM_ABBR.get(aname, aname[:3].upper())
            if team and team.upper() not in (habbr, aabbr):
                continue

            feed_url = f"https://statsapi.mlb.com/api/v1.1/game/{gpk}/feed/live"
            feed = requests.get(feed_url, timeout=30).json()
            all_plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
            for play in all_plays:
                about = play.get("about", {})
                inning = about.get("inning", 1)
                topbot = "Top" if about.get("isTopInning", True) else "Bot"
                matchup = play.get("matchup", {})
                batter_id = matchup.get("batter", {}).get("id")
                batter_name = matchup.get("batter", {}).get("fullName", "")
                pitcher_id = matchup.get("pitcher", {}).get("id")
                pitcher_name = matchup.get("pitcher", {}).get("fullName", "")
                stand = matchup.get("batSide", {}).get("code", "")
                p_throws = matchup.get("pitchHand", {}).get("code", "")
                play_result = play.get("result", {})
                play_des = play_result.get("description", "")
                play_event = play_result.get("eventType", "")

                play_events = play.get("playEvents", [])
                pitch_events = [ev for ev in play_events if ev.get("isPitch")]
                for idx, ev in enumerate(pitch_events):
                    is_last = (idx == len(pitch_events) - 1)
                    details = ev.get("details", {})
                    pdata = ev.get("pitchData", {})
                    coords = pdata.get("coordinates", {})
                    breaks = pdata.get("breaks", {})
                    hdata = ev.get("hitData", {})
                    count = ev.get("count", {})

                    rows.append({
                        "pitch_type": details.get("type", {}).get("code"),
                        "game_date": gdate,
                        "release_speed": pdata.get("startSpeed"),
                        "release_pos_x": coords.get("x0"),
                        "release_pos_z": coords.get("z0"),
                        "player_name": batter_name,
                        "batter": batter_id,
                        "pitcher": pitcher_id,
                        "events": play_event if is_last else None,
                        "description": details.get("description"),
                        "spin_dir": breaks.get("spinDirection"),
                        "zone": pdata.get("zone"),
                        "des": play_des if is_last else None,
                        "game_type": gtype,
                        "stand": stand,
                        "p_throws": p_throws,
                        "home_team": habbr,
                        "away_team": aabbr,
                        "type": details.get("call", {}).get("code"),
                        "hit_location": int(hdata["location"]) if str(hdata.get("location", "")).isdigit() else None,
                        "bb_type": hdata.get("trajectory"),
                        "balls": count.get("balls"),
                        "strikes": count.get("strikes"),
                        "game_year": gyear,
                        "pfx_x": coords.get("pfxX"),
                        "pfx_z": coords.get("pfxZ"),
                        "plate_x": coords.get("pX"),
                        "plate_z": coords.get("pZ"),
                        "on_3b": None,
                        "on_2b": None,
                        "on_1b": None,
                        "outs_when_up": count.get("outs"),
                        "inning": inning,
                        "inning_topbot": topbot,
                        "launch_speed": hdata.get("launchSpeed"),
                        "launch_angle": hdata.get("launchAngle"),
                        "effective_speed": pdata.get("endSpeed"),
                        "release_spin_rate": breaks.get("spinRate"),
                        "release_extension": pdata.get("extension"),
                        "game_pk": gpk,
                        "pitcher_name": pitcher_name,
                        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    })
    return pd.DataFrame(rows)


def pull_statcast(start_date: str, end_date: str, team: str = None) -> int:
    init_db()
    try:
        from pybaseball import statcast
    except ImportError:
        print("[!] pybaseball not found, attempting pip install inside venv...", file=sys.stderr)
        return 0

    print(f"[*] Querying Baseball Savant: {start_date} to {end_date} (team={team or 'ALL'})...")
    try:
        if team:
            df = statcast(start_dt=start_date, end_dt=end_date, team=team.upper())
        else:
            df = statcast(start_dt=start_date, end_dt=end_date)

        if df is None or df.empty:
            print(f"[*] Savant CSV index pending for {start_date} to {end_date}; pulling pitch-by-pitch Statcast from MLB Live Feed v1.1...")
            df = fetch_live_statcast_fallback(start_date, end_date, team)

        if df is None or df.empty:
            print(f"[-] No Statcast records returned for {start_date} to {end_date}.")
            return 0

        conn = sqlite3.connect(DB_PATH)
        existing_cols = {r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
        valid_cols = [c for c in df.columns if c in existing_cols]
        df_valid = df[valid_cols]

        # Idempotent delete before insert for overlapping game_pks in this window
        if "game_pk" in df_valid.columns:
            gpks = [int(x) for x in df_valid["game_pk"].dropna().unique()]
            if gpks:
                placeholders = ",".join("?" for _ in gpks)
                conn.execute(f"DELETE FROM {TABLE_NAME} WHERE game_pk IN ({placeholders})", gpks)

        df_valid.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
        conn.commit()
        conn.close()
        print(f"[✔] Successfully ingested {len(df_valid)} Statcast pitches into {DB_PATH.name}.")
        return len(df_valid)
    except Exception as e:
        print(f"[-] Baseball Savant fetch error: {e}", file=sys.stderr)
        return 0


def main():
    parser = argparse.ArgumentParser(description="Baseball Savant Statcast Puller")
    parser.add_argument("--date", help="Specific game date YYYY-MM-DD")
    parser.add_argument("--today", action="store_true", help="Fetch today's games")
    parser.add_argument("--team", help="Filter by team abbreviation (e.g. CLE, TB, MIL)")
    parser.add_argument("--days", type=int, default=1, help="Number of preceding days to backfill")
    args = parser.parse_args()

    if args.today:
        target_date = date.today().strftime("%Y-%m-%d")
        start_date = (date.today() - timedelta(days=args.days - 1)).strftime("%Y-%m-%d")
        pull_statcast(start_date, target_date, args.team)
    elif args.date:
        pull_statcast(args.date, args.date, args.team)
    else:
        target_date = date.today().strftime("%Y-%m-%d")
        pull_statcast(target_date, target_date, args.team)


if __name__ == "__main__":
    main()
