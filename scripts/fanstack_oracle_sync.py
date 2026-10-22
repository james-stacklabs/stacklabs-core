import argparse
import os
import shutil
import sys
import requests

def get_team_abbrevs(game_pk):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        away = data.get('gameData', {}).get('teams', {}).get('away', {}).get('abbreviation', 'AWAY')
        home = data.get('gameData', {}).get('teams', {}).get('home', {}).get('abbreviation', 'HOME')
        return away, home
    except Exception as e:
        print(f"Warning: Failed to fetch team data from MLB API: {e}")
        return "AWAY", "HOME"

def main():
    parser = argparse.ArgumentParser(description="Snapshot FanStack active logs for the Oracle payload dropzone (Rule 81).")
    parser.add_argument("--game_pk", required=True, help="MLB Game PK")
    parser.add_argument("--milestone", required=True, help="Milestone label (e.g., Pregame, 7th_Inning, Postgame)")
    args = parser.parse_args()

    game_pk = args.game_pk
    milestone = args.milestone

    # Paths
    base_dir = "/home/james/stacklabs"
    source_log = os.path.join(base_dir, "08_FanStack", "logs", f"auto_export_{game_pk}.md")
    dest_dir = os.path.join(base_dir, "dna", "agents", "SOVEREIGN_FANSTACK_ORACLE", "payloads")

    if not os.path.exists(source_log):
        print(f"Error: Source log not found at {source_log}")
        sys.exit(1)

    os.makedirs(dest_dir, exist_ok=True)

    # Get team abbreviations
    away_abbr, home_abbr = get_team_abbrevs(game_pk)

    # Output filename per Rule 81: {AWAY}_at_{HOME}_{game_pk}_{milestone}.md.txt
    dest_filename = f"{away_abbr}_at_{home_abbr}_{game_pk}_{milestone}.md.txt"
    dest_path = os.path.join(dest_dir, dest_filename)

    try:
        shutil.copy2(source_log, dest_path)
        print(f"SUCCESS (Rule 81): Copied live log to {dest_path}")
    except Exception as e:
        print(f"Error copying log: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
