import csv
import urllib.request
from io import StringIO
import os

EXPORT_DIR = "/home/james/stacklabs/dna/notebook_lm_exports"
# Fetching the 2026 season for NotebookLM ingestion.
CSV_URL = "https://baseballsavant.mlb.com/statcast_search/csv?all=true&game_date_gt=2026-03-20&game_date_lt=2026-04-21&team=NYM&type=details"

def download_and_export_packs():
    print(f"[*] Fetching Mets game data packs for NotebookLM ingestion...")
    req = urllib.request.Request(
        CSV_URL, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            csv_data = response.read().decode('utf-8')
    except Exception as e:
        print(f"[!] Error fetching from MLB Savant: {e}")
        return False

    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    reader = csv.DictReader(StringIO(csv_data))
    games = {}
    
    # Savant gives newest pitches first. We just want to group by game.
    for row in reader:
        game_pk = row.get('game_pk')
        if not game_pk:
            continue
            
        if game_pk not in games:
            games[game_pk] = {
                'date': row.get('game_date', ''),
                'home': row.get('home_team', ''),
                'away': row.get('away_team', ''),
                'rows': []
            }
        games[game_pk]['rows'].append(row)

    print(f"[*] Found {len(games)} unique games in the skid sequence.")
    
    # Export one CSV game pack per game for NotebookLM
    fieldnames = reader.fieldnames
    
    for game_pk, data in games.items():
        date_str = data['date']
        filename = f"{EXPORT_DIR}/game_pack_{date_str}_{data['away']}_at_{data['home']}_{game_pk}.csv"
        
        # Reverse rows to make it chronological
        data['rows'].reverse()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data['rows'])
            
        print(f"  -> Exported: {filename} ({len(data['rows'])} pitches)")

    print("[*] All game packs prepared for NotebookLM!")
    return True

if __name__ == "__main__":
    download_and_export_packs()
