#!/usr/bin/env python3
import sqlite3
import requests
import datetime
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def init_db():
    print(f"[ROSTER SYNC] Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    cursor = conn.cursor()
    
    # Create the mlb_rosters table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mlb_rosters (
            sys_id TEXT PRIMARY KEY,
            player_name TEXT NOT NULL,
            team_abbr TEXT NOT NULL,
            team_full TEXT NOT NULL,
            position TEXT,
            jersey_number TEXT,
            status TEXT DEFAULT 'active',
            last_updated TEXT DEFAULT (datetime('now'))
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rosters_team ON mlb_rosters(team_abbr)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rosters_player ON mlb_rosters(player_name)")
    
    conn.commit()
    conn.close()

def sync_rosters():
    # 1. Fetch all teams from StatsAPI
    print("[ROSTER SYNC] Fetching team listings from MLB StatsAPI...")
    try:
        teams_url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
        teams_resp = requests.get(teams_url, timeout=10)
        teams_resp.raise_for_status()
        teams_data = teams_resp.json()
        teams = teams_data.get("teams", [])
    except Exception as e:
        print(f"[ROSTER SYNC ERROR] Failed to fetch teams: {e}", file=sys.stderr)
        return False

    if not teams:
        print("[ROSTER SYNC ERROR] No teams found in StatsAPI response.", file=sys.stderr)
        return False

    print(f"[ROSTER SYNC] Found {len(teams)} teams. Processing active 26-man rosters...")
    
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    cursor = conn.cursor()
    
    sync_timestamp = datetime.datetime.now().isoformat()
    total_players = 0

    for idx, team in enumerate(teams):
        team_id = team.get("id")
        team_abbr = team.get("abbreviation")
        team_full = team.get("name")
        
        if not team_id or not team_abbr:
            continue
            
        # Standardize abbreviation mapping if needed, e.g. OAK -> ATH
        # But StatsAPI already returns ATH for Athletics in 2026.
        team_abbr = team_abbr.upper()
        
        print(f"[{idx+1}/{len(teams)}] Syncing {team_full} ({team_abbr})...")
        
        try:
            roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster/active"
            roster_resp = requests.get(roster_url, timeout=10)
            roster_resp.raise_for_status()
            roster_data = roster_resp.json()
            roster_list = roster_data.get("roster", [])
        except Exception as e:
            print(f"  [WARNING] Failed to fetch roster for {team_abbr}: {e}", file=sys.stderr)
            continue

        for player in roster_list:
            person = player.get("person", {})
            player_id = person.get("id")
            player_name = person.get("fullName")
            jersey_number = player.get("jerseyNumber", "")
            pos_abbr = player.get("position", {}).get("abbreviation", "")
            status_desc = player.get("status", {}).get("description", "Active")
            
            if not player_id or not player_name:
                continue
                
            sys_id = f"{team_abbr}_{player_id}"
            
            cursor.execute("""
                INSERT OR REPLACE INTO mlb_rosters (
                    sys_id, player_name, team_abbr, team_full, position, jersey_number, status, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sys_id, player_name, team_abbr, team_full, pos_abbr, jersey_number, status_desc, sync_timestamp))
            
            total_players += 1

    # Clean up stale roster entries that were not updated during this sync run
    # (keeps the roster table strictly synchronized to the latest StatsAPI 40-man state)
    cursor.execute("DELETE FROM mlb_rosters WHERE last_updated != ?", (sync_timestamp,))
    deleted_stale = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"[ROSTER SYNC COMPLETE] Successfully synchronized {total_players} players. Removed {deleted_stale} stale entries.")
    return True

def main():
    init_db()
    success = sync_rosters()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
