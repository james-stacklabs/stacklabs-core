import requests
from bs4 import BeautifulSoup
import os
import subprocess
import json
import csv
from datetime import datetime

CONTEXT_FILE = '/home/james/stacklabs/scripts/fanstack_live_context.txt'
EXPORT_JSON = '/home/james/stacklabs/01_Sovereign_Portal/public/personas.json'
EXPORT_CSV = '/home/james/stacklabs/dna/personas_spreadsheet_full.csv'
EXPORT_SCRIPT = '/home/james/stacklabs/01_Sovereign_Portal/scripts/export_personas.py'

def run():
    print(f"=== [PHASE 0] REAL-TIME ROSTER GROUNDING ===")
    print("> Running roster synchronization script...")
    try:
        env = os.environ.copy()
        res = subprocess.run(["/home/james/stacklabs/.venv/bin/python", "/home/james/stacklabs/scripts/roster_sync.py"], env=env, capture_output=True, text=True)
        if res.returncode == 0:
            print("> Roster synchronization completed successfully.")
            for line in res.stdout.split("\n"):
                if "Successfully synchronized" in line:
                    print(f"  {line}")
        else:
            print(f"> Roster synchronization failed with code {res.returncode}: {res.stderr}")
    except Exception as e:
        print(f"> Failed to execute roster synchronization: {e}")

    print(f"\n=== [PHASE 1] CONTEXT INJECTION ===")
    
    # 1. Fetch Schedule
    print("> Querying MLB Stats API...")
    try:
        schedule_res = requests.get('https://statsapi.mlb.com/api/v1/schedule?sportId=1')
        schedule_data = schedule_res.json()
        games = schedule_data.get('dates', [{}])[0].get('games', [])
        
        schedule_text = f"MLB SCHEDULE FOR {datetime.now().strftime('%Y-%m-%d')}:\n"
        for g in games[:10]: # Top 10 matches
            away = g.get('teams', {}).get('away', {}).get('team', {}).get('name', 'Unknown')
            home = g.get('teams', {}).get('home', {}).get('team', {}).get('name', 'Unknown')
            status = g.get('status', {}).get('detailedState', 'Unknown')
            schedule_text += f"- {away} @ {home} [{status}]\n"
            
    except Exception as e:
        schedule_text = f"Failed to load schedule: {e}\n"
        
    # 2. Scrape Yardbarker
    print("> Scraping Yardbarker MLB News...")
    try:
        yb_res = requests.get('https://www.yardbarker.com/mlb', headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(yb_res.text, 'html.parser')
        headlines = []
        for a in soup.select('.article_title_link')[:5]:
            headlines.append(a.text.strip())
        news_text = "\nRECENT BIZARRE/NOTABLE NEWS:\n" + "\n".join(f"- {h}" for h in headlines)
    except Exception as e:
        news_text = f"\nFailed to load news: {e}\n"
        
    # 3. Update Ledger
    with open(CONTEXT_FILE, 'w') as f:
        f.write(schedule_text + news_text)
    print(f"> Context injected into {CONTEXT_FILE}")
    
    print(f"\n=== [PHASE 2] ROSTER EXPORT ===")
    print(f"> Running existing export script...")
    env = os.environ.copy()
    subprocess.run(["/home/james/stacklabs/.venv/bin/python", EXPORT_SCRIPT], env=env)
    
    print("> Translating JSON to CSV...")
    with open(EXPORT_JSON, 'r') as f:
        personas = json.load(f)
        
    if personas:
        keys = personas[0].keys()
        with open(EXPORT_CSV, 'w', newline='') as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(personas)
        print(f"> Generated {EXPORT_CSV} for review.")
    else:
        print("> ERROR: No personas exported.")
        
if __name__ == '__main__':
    run()
