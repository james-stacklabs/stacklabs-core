#!/usr/bin/env python3
"""
seed_schedule.py
Parses a local MLB schedule JSON payload and upserts matchups into the mlb_schedule table.

Usage:
    python3 seed_schedule.py --file /home/james/stacklabs/data/today_schedule.json
"""

import sys
import os
import json
import sqlite3
import argparse

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

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
    'Athletics': 'OAK',
}

def abbr(name: str) -> str:
    return TEAM_ABBR.get(name, name[:3].upper())

def parse_schedule_json(file_path: str) -> list[dict]:
    if not os.path.exists(file_path):
        print(f"[ERROR] Schedule JSON file not found at: {file_path}")
        sys.exit(1)

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read or parse JSON file: {e}")
        sys.exit(1)

    games = []
    for date_block in data.get('dates', []):
        game_date = date_block.get('date', '')
        for g in date_block.get('games', []):
            game_pk   = str(g.get('gamePk', ''))
            status    = g.get('status', {}).get('detailedState', 'Scheduled')
            teams     = g.get('teams', {})
            home_name = teams.get('home', {}).get('team', {}).get('name', '')
            away_name = teams.get('away', {}).get('team', {}).get('name', '')
            home_abbr = teams.get('home', {}).get('team', {}).get('abbreviation', '') or abbr(home_name)
            away_abbr = teams.get('away', {}).get('team', {}).get('abbreviation', '') or abbr(away_name)
            game_time = g.get('gameDate', '')
            venue     = g.get('venue', {}).get('name', '')

            games.append({
                'game_pk':   game_pk,
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
        print("[INFO] No games found in schedule payload.")
        return 0

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executemany("""
        INSERT INTO mlb_schedule (game_pk, game_date, game_time, home_team, away_team, venue, status)
        VALUES (:game_pk, :game_date, :game_time, :home_team, :away_team, :venue, :status)
        ON CONFLICT(game_pk) DO UPDATE SET
            game_date  = excluded.game_date,
            game_time  = excluded.game_time,
            home_team  = excluded.home_team,
            away_team  = excluded.away_team,
            venue      = excluded.venue,
            status     = excluded.status
    """, games)
    conn.commit()
    inserted = c.rowcount
    conn.close()
    return inserted

def main():
    parser = argparse.ArgumentParser(description='Seed MLB schedule from local JSON')
    parser.add_argument('--file', required=True, help='Path to schedule JSON file')
    args = parser.parse_args()

    print(f"[seed_schedule] Parsing schedule from local file: {args.file}")
    games = parse_schedule_json(args.file)
    print(f"[seed_schedule] Extracted {len(games)} games from JSON payload")

    count = upsert_games(games)
    print(f"[seed_schedule] Upserted {count} games into mlb_schedule table.")

if __name__ == '__main__':
    main()
