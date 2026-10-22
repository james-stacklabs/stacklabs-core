#!/usr/bin/env python3
"""
sync_mlb_schedule.py
Pulls the full MLB regular season schedule from the Stats API and
upserts every game into the local mlb_schedule table.

Usage:
    python3 sync_mlb_schedule.py              # syncs full 2026 season
    python3 sync_mlb_schedule.py --today      # refreshes today only (fast)
    python3 sync_mlb_schedule.py --days 7     # next 7 days only

Run this script in fanstack_daily_prep to keep status (Postponed,
Final, etc.) fresh. A Postponed game will never get persona rooms
spun up by populate_rooms.py.
"""

import sqlite3
import requests
import argparse
from datetime import date, timedelta

DB_PATH    = '/home/james/stacklabs/dna/sovereign_now.db'
MLB_API    = 'https://statsapi.mlb.com/api/v1/schedule'
SPORT_ID   = 1          # MLB
SEASON     = 2026
GAME_TYPES = 'R,F,D,L,W,P'  # R=Regular, F=Wild Card, D=Division, L=League Champ, W=World Series, P=Postseason

# Team abbreviation lookup — MLB API uses full names in some responses
TEAM_ABBR: dict[str, str] = {
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
    # Handle abbreviations the API sometimes returns directly
    'Athletics': 'OAK',
}

def abbr(name: str) -> str:
    return TEAM_ABBR.get(name, name[:3].upper())


def fetch_games(start: str, end: str, game_types: str = GAME_TYPES) -> list[dict]:
    """Fetch games from MLB Stats API for a date range."""
    params = {
        'sportId': SPORT_ID,
        'season': SEASON,
        'gameType': game_types,
        'startDate': start,
        'endDate': end,
        'fields': 'dates,date,games,gamePk,gameType,gameDate,status,detailedState,teams,home,away,team,name,abbreviation,venue,name'
    }
    try:
        res = requests.get(MLB_API, params=params, timeout=30)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f'[ERROR] MLB API request failed: {e}')
        return []

    games = []
    for date_block in data.get('dates', []):
        game_date = date_block.get('date', '')
        for g in date_block.get('games', []):
            game_pk   = str(g.get('gamePk', ''))
            game_type = g.get('gameType', 'R')
            status    = g.get('status', {}).get('detailedState', 'Scheduled')
            teams     = g.get('teams', {})
            home_name = teams.get('home', {}).get('team', {}).get('name', '')
            away_name = teams.get('away', {}).get('team', {}).get('name', '')
            # Some endpoints return abbreviation directly
            home_abbr = teams.get('home', {}).get('team', {}).get('abbreviation', '') or abbr(home_name)
            away_abbr = teams.get('away', {}).get('team', {}).get('abbreviation', '') or abbr(away_name)
            game_time = g.get('gameDate', '')
            venue     = g.get('venue', {}).get('name', '')
            games.append({
                'game_pk':   game_pk,
                'game_type': game_type,
                'game_date': game_date,
                'game_time': game_time,
                'home_team': home_abbr,
                'away_team': away_abbr,
                'venue':     venue,
                'status':    status,
            })
    return games


def upsert_games(games: list[dict]) -> int:
    if not games:
        return 0
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executemany("""
        INSERT INTO sport_schedule (game_pk, sport, game_type, game_date, game_time, home_team, away_team, venue, status)
        VALUES (:game_pk, 'MLB', :game_type, :game_date, :game_time, :home_team, :away_team, :venue, :status)
        ON CONFLICT(game_pk) DO UPDATE SET
            sport      = 'MLB',
            game_type  = excluded.game_type,
            game_date  = excluded.game_date,
            game_time  = excluded.game_time,
            home_team  = excluded.home_team,
            away_team  = excluded.away_team,
            venue      = excluded.venue,
            status     = excluded.status,
            sys_updated_on = CURRENT_TIMESTAMP
    """, games)
    conn.commit()
    inserted = c.rowcount
    conn.close()
    return inserted


def main():
    parser = argparse.ArgumentParser(description='Sync MLB schedule to Sovereign DB')
    parser.add_argument('--today', action='store_true', help='Sync today only')
    parser.add_argument('--days',  type=int, default=None, help='Sync next N days')
    parser.add_argument('--postseason', action='store_true', help='Sync full postseason window (Oct 1 → Nov 5)')
    args = parser.parse_args()

    today = date.today()
    game_types = GAME_TYPES

    if args.today:
        start = end = today.isoformat()
        label = 'today'
    elif args.days:
        start = today.isoformat()
        end   = (today + timedelta(days=args.days)).isoformat()
        label = f'next {args.days} days'
    elif args.postseason:
        start = f'{SEASON}-09-29'
        end   = f'{SEASON}-11-05'
        game_types = 'F,D,L,W,P'
        label = f'{SEASON} postseason'
    else:
        # Full season + postseason: March 1 → November 5
        start = f'{SEASON}-03-01'
        end   = f'{SEASON}-11-05'
        label = f'full {SEASON} season + postseason'

    print(f'[sync_mlb_schedule] Fetching {label} ({start} → {end})...')
    games = fetch_games(start, end, game_types)
    print(f'[sync_mlb_schedule] Fetched {len(games)} games from MLB API')

    count = upsert_games(games)
    print(f'[sync_mlb_schedule] Upserted {count} rows into mlb_schedule')

    # Summary of today's slate
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT game_pk, game_type, away_team, home_team, game_time, status FROM mlb_schedule WHERE game_date=? ORDER BY game_pk",
              (today.isoformat(),))
    rows = c.fetchall()
    conn.close()

    if rows:
        print(f"\n[Today's Slate — {today}]")
        for pk, gtype, away, home, gtime, st in rows:
            flag = '🚫' if 'Postponed' in st or 'Suspended' in st else '⚾'
            print(f'  {flag} {pk} [{gtype}]  {away} @ {home}  ({gtime})  [{st}]')
    else:
        print(f'  No games found for {today}')


if __name__ == '__main__':
    main()
