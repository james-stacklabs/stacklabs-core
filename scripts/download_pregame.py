import sys
import json
import os

try:
    import statsapi
except ImportError:
    print("statsapi not installed, run pip install MLB-StatsAPI")
    sys.exit(1)

def fetch_data():
    mets_id = 121
    sf_id = 137

    print("[*] Fetching NYM roster...")
    nym_roster = statsapi.get('team_roster', {'teamId': mets_id, 'rosterType': 'active'})
    print("[*] Fetching SF roster...")
    sf_roster = statsapi.get('team_roster', {'teamId': sf_id, 'rosterType': 'active'})
    
    print("[*] Fetching NYM season stats...")
    nym_stats = statsapi.get('team_stats', {'teamId': mets_id, 'group': 'hitting,pitching', 'stats': 'season', 'season': '2026'})
    print("[*] Fetching SF season stats...")
    sf_stats = statsapi.get('team_stats', {'teamId': sf_id, 'group': 'hitting,pitching', 'stats': 'season', 'season': '2026'})

    data = {
        "matchup": "NYM@SF",
        "date": "2026-04-02",
        "nym": {"roster": nym_roster, "stats": nym_stats},
        "sf": {"roster": sf_roster, "stats": sf_stats}
    }

    out_path = '/home/james/stacklabs/scripts/pregame_4_2.json'
    with open(out_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"[+] Pregame data saved to {out_path}")

if __name__ == '__main__':
    fetch_data()
