#!/usr/bin/env python3
import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

TEAM_COLORS = {
    "LAD": "#005A9C",
    "NYY": "#0C2340",
    "CHC": "#0E3386",
    "NYM": "#FF6B00",
    "MIN": "#D31145",
    "DET": "#0C2340",
    "PIT": "#FDB827",
    "SF": "#FD5A1E",
    "TEX": "#003278",
    "TOR": "#134A8E",
    "OAK": "#003831",
    "PHI": "#E81828",
    "MIA": "#00A3E0",
    "ATL": "#13274F",
    "COL": "#333366",
    "SD": "#2F241D",
    "WSH": "#AB0003",
    "CLE": "#E31937",
    "STL": "#C41E3A",
    "MIL": "#12284C",
    "BAL": "#DF4601",
    "BOS": "#BD3039",
    "CWS": "#27251F",
    "ARI": "#A71930",
    "HOU": "#EB6E1F",
    "KC": "#004687",
    "SEA": "#0C2C56",
    "GLOBAL": "#0d9488"
}

REVERTS = {
    "sodo_mojo_marty": "SEA",
    "trident_truther": "SEA",
    "king_felix_fanatic": "SEA",
    "peagle_prophet": "TEX",
    "boomstick_bobby": "TEX",
    "curly_w_wally": "WSH",
    "wavy_gravy": "SF",
    "bendix_burnout": "NYY",
    "comiskey_ghost": "SEA",
    "fog_horn_frank": "SF"
}

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for user_name, team in REVERTS.items():
        color = TEAM_COLORS[team]
        print(f"Restoring @{user_name} to {team}...")

        # Update persona table
        cur.execute("""
            UPDATE persona SET 
                team = ?,
                color = ?,
                updated_at = datetime('now')
            WHERE LOWER(user_name) = ?
        """, (team, color, user_name))

        # Update sys_user table
        cur.execute("""
            UPDATE sys_user SET
                department = ?,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE LOWER(user_name) = ?
        """, (team, user_name))

        # Update cmdb_ci table
        cur.execute("""
            UPDATE cmdb_ci SET
                assigned_to = ?,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE name = ?
        """, (team, user_name))

    conn.commit()
    conn.close()
    print("Restore complete.")

if __name__ == "__main__":
    main()
