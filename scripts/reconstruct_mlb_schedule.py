#!/usr/bin/env python3
import sqlite3
import json
import os

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
OUTPUT_PATH = '/home/james/stacklabs/01_Sovereign_Portal/public/mlb_schedule_2026.json'

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query all games where NYM is playing
    cursor.execute("""
        SELECT game_pk, game_date, home_team, away_team 
        FROM mlb_schedule 
        WHERE home_team = 'NYM' OR away_team = 'NYM'
        ORDER BY game_date
    """)
    rows = cursor.fetchall()
    conn.close()

    schedule = []
    for row in rows:
        try:
            game_pk = int(row[0])
        except (ValueError, TypeError):
            continue
        
        game_date = row[1]
        home_team = row[2]
        away_team = row[3]
        
        if home_team == 'NYM':
            opponent = away_team
            game = f"{away_team} @ NYM"
        else:
            opponent = home_team
            game = f"NYM @ {home_team}"
            
        schedule.append({
            "date": game_date,
            "game": game,
            "opponent": opponent,
            "gamePk": game_pk
        })

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(schedule, f, indent=4)

    print(f"[SUCCESS] Exported {len(schedule)} NYM games to {OUTPUT_PATH}")

if __name__ == '__main__':
    main()
