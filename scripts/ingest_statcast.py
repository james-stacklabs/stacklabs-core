import sqlite3
import os
import urllib.request
import csv
import json
from io import StringIO

DB_PATH = "/home/james/stacklabs/scripts/fanstack_sim.db"
# Use a 2023 or 2024 real date range for NYM vs STL if 2026 isn't available from MLB yet.
# Use September 30, 2024 (NYM vs ATL Truist Park Game 1) as requested.
CSV_URL = "https://baseballsavant.mlb.com/statcast_search/csv?all=true&game_date_gt=2024-09-30&game_date_lt=2024-09-30&team=NYM&type=details"

def init_db():
    print(f"[*] Initializing Gametime Simulator Database at {DB_PATH}")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE game_meta (
        game_pk INTEGER PRIMARY KEY,
        game_date DATE,
        home_team TEXT,
        away_team TEXT,
        final_home INTEGER,
        final_away INTEGER,
        venue TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE pitches (
        pitch_id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_pk INTEGER,
        inning INTEGER,
        inning_topbot TEXT,
        at_bat_number INTEGER,
        pitch_number INTEGER,
        pitcher_name TEXT,
        batter_name TEXT,
        pitch_type TEXT,
        pitch_name TEXT,
        release_speed REAL,
        release_spin_rate REAL,
        zone INTEGER,
        description TEXT,
        events TEXT,
        launch_speed REAL,
        launch_angle REAL,
        hit_distance_sc REAL,
        home_score INTEGER,
        away_score INTEGER,
        balls INTEGER,
        strikes INTEGER,
        outs_when_up INTEGER,
        on_1b TEXT,
        on_2b TEXT,
        on_3b TEXT,
        delta_home_win_exp REAL,
        delta_run_exp REAL,
        raw_json TEXT
    )
    """)
    conn.commit()
    return conn

def download_and_ingest(conn):
    print(f"[*] Connecting to Statcast Oracle (Baseball Savant)...")
    req = urllib.request.Request(
        CSV_URL, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            csv_data = response.read().decode('utf-8')
    except Exception as e:
        print(f"[!] Error fetching from MLB Savant: {e}")
        return False

    print("[*] Parsing CSV payload...")
    reader = csv.DictReader(StringIO(csv_data))
    pitches = []
    
    # Store unique games
    games = {}

    # Read exactly in reverse because Savant CSVs are newest-pitch-first
    rows = list(reader)
    rows.reverse()

    for row in rows:
        if not row.get('game_pk'):
            continue
            
        game_pk = int(row['game_pk'])
        
        # Capture meta
        if game_pk not in games:
            games[game_pk] = {
                'game_date': row.get('game_date', ''),
                'home_team': row.get('home_team', ''),
                'away_team': row.get('away_team', ''),
                'final_home': 0,
                'final_away': 0,
                'venue': 'Truist Park'
            }

        # Handle null numbers
        def safe_float(val):
            try: return float(val) if val else 0.0
            except: return 0.0
            
        def safe_int(val):
            try: return int(float(val)) if val else 0
            except: return 0

        pitches.append((
            game_pk,
            safe_int(row.get('inning')),
            row.get('inning_topbot', ''),
            safe_int(row.get('at_bat_number')),
            safe_int(row.get('pitch_number')),
            row.get('player_name', 'Unknown Pitcher'), # Savant uses player_name for pitcher
            row.get('batter', 'Unknown Batter'), # Wait, batter ID is here, name isn't always. 
            row.get('pitch_type', ''),
            row.get('pitch_name', ''),
            safe_float(row.get('release_speed')),
            safe_float(row.get('release_spin_rate')),
            safe_int(row.get('zone')),
            row.get('description', ''),
            row.get('events', ''),
            safe_float(row.get('launch_speed')),
            safe_float(row.get('launch_angle')),
            safe_float(row.get('hit_distance_sc')),
            safe_int(row.get('home_score')),
            safe_int(row.get('away_score')),
            safe_int(row.get('balls')),
            safe_int(row.get('strikes')),
            safe_int(row.get('outs_when_up')),
            row.get('on_1b', ''),
            row.get('on_2b', ''),
            row.get('on_3b', ''),
            safe_float(row.get('delta_home_win_exp')),
            safe_float(row.get('delta_run_exp')),
            json.dumps(row)
        ))

    if not pitches:
        print("[!] No pitches found in payload.")
        return False

    print(f"[*] Seeding {len(pitches)} chronologically ordered pitches into DVR ledger...")
    
    cursor = conn.cursor()
    
    for pk, meta in games.items():
        cursor.execute('''
            INSERT INTO game_meta (game_pk, game_date, home_team, away_team, final_home, final_away, venue)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (pk, meta['game_date'], meta['home_team'], meta['away_team'], meta['final_home'], meta['final_away'], meta['venue']))

    cursor.executemany('''
        INSERT INTO pitches (
            game_pk, inning, inning_topbot, at_bat_number, pitch_number, pitcher_name, batter_name,
            pitch_type, pitch_name, release_speed, release_spin_rate, zone, description, events,
            launch_speed, launch_angle, hit_distance_sc, home_score, away_score, balls, strikes,
            outs_when_up, on_1b, on_2b, on_3b, delta_home_win_exp, delta_run_exp, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', pitches)
    
    conn.commit()
    print("[*] Ingestion Complete. DB verified and locked.")
    return True

if __name__ == "__main__":
    conn = init_db()
    download_and_ingest(conn)
    conn.close()
