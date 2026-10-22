#!/usr/bin/env python3
import os
import re
import sqlite3
import glob

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
    "GLOBAL": "#0d9488"
}

# Manual overrides for high-confidence specific cases to ensure perfect precision
MANUAL_OVERRIDES = {
    "steel_city_sufferer": "PIT",
    "steel_city_steve": "PIT",
    "ivy_inspector_ian": "CHC",
    "ivy_truther": "CHC",
    "comiskey_spy": "CWS",
    "screech_supporter": "WSH",
    "bleacher_bum_bailout": "CHC",
    "dinger_defender": "COL",
    "train_horn_terry": "HOU",
    "lake_effect_larry": "CLE",
    "drum_line_dan": "CLE",
    "bo_jackson_truther": "CLE"
}

def parse_blueprint(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    handle_match = re.search(r"\*\*X Handle:\*\*\s*`@?(\w+)`", content)
    display_name_match = re.search(r"\*\*Display Name:\*\*\s*(.+)", content)
    team_match = re.search(r"\*\*Team:\*\*\s*(.+)", content)

    if not handle_match:
        return None

    handle = handle_match.group(1).strip()
    display_name = display_name_match.group(1).strip() if display_name_match else handle
    team = team_match.group(1).strip() if team_match else "GLOBAL"

    # Clean display name from markdown formatting
    display_name = display_name.replace('**', '').replace('"', '').strip()

    return {
        "handle": handle,
        "display_name": display_name,
        "team": team,
        "filepath": filepath
    }

def detect_team_from_content(user_name, display_name, prompt, lore):
    user_name_lower = user_name.lower()
    display_name_lower = display_name.lower()

    # 1. Manual Overrides (Highest Priority)
    if user_name_lower in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[user_name_lower]

    # 2. Check explicit Allegiance/Team declaration in prompt
    m = re.search(r'Allegiance\s*/\s*Team[^A-Za-z0-9]*([A-Za-z0-9_]+)', prompt, re.IGNORECASE)
    if m:
        val = m.group(1).strip().upper()
        if val in TEAM_COLORS:
            return val
        if val == "WAS": return "WSH"
        if val == "CLE": return "CLE"
        if "PIRATES" in val: return "PIT"
        if "CUBS" in val: return "CHC"
        if "METS" in val: return "NYM"
        if "WHITE SOX" in val: return "CWS"
        if "ASTROS" in val: return "HOU"
        if "ROCKIES" in val: return "COL"
        if "GUARDIANS" in val or "INDIANS" in val: return "CLE"

    # 3. High-confidence username/display name keywords
    if 'steel_city' in user_name_lower or 'welfare_bucco' in user_name_lower or 'bucco' in user_name_lower:
        return 'PIT'
    if 'cubs' in user_name_lower or 'cubbie' in user_name_lower or 'wrigley' in user_name_lower or 'bartman' in user_name_lower:
        return 'CHC'
    if 'screech_supporter' in user_name_lower or 'nats' in user_name_lower:
        return 'WSH'
    if 'comiskey' in user_name_lower or 'southside' in user_name_lower:
        return 'CWS'
    if 'dinger' in user_name_lower or 'coors' in user_name_lower:
        return 'COL'
    if 'drum_line' in user_name_lower or 'lake_effect' in user_name_lower:
        return 'CLE'
    if 'train_horn' in user_name_lower:
        return 'HOU'
    if 'mets' in user_name_lower or 'nym' in user_name_lower or '7_train' in user_name_lower:
        return 'NYM'

    # 4. Fall back to search in text
    text_lower = f"{prompt} {lore}".lower()
    if 'pittsburgh pirates' in text_lower or 'pittsburgh buccos' in text_lower or 'pnc park' in text_lower:
        return 'PIT'
    if 'wrigley field' in text_lower or 'chicago cubs' in text_lower or 'wrigley bleachers' in text_lower:
        return 'CHC'
    if 'washington nationals' in text_lower or 'curly w' in text_lower or 'nationals park' in text_lower:
        return 'WSH'
    if 'coors field' in text_lower or 'colorado rockies' in text_lower:
        return 'COL'
    if 'minute maid park' in text_lower or 'houston astros' in text_lower:
        return 'HOU'
    if 'progressive field' in text_lower or 'cleveland guardians' in text_lower or 'cleveland indians' in text_lower:
        return 'CLE'
    if 'comiskey park' in text_lower or 'chicago white sox' in text_lower or 'guaranteed rate field' in text_lower:
        return 'CWS'

    return None

def main():
    blueprints = []
    # Scan personas in both directories
    for filepath in glob.glob("/home/james/stacklabs/dna/personas/*_onboarding.md") + \
                    glob.glob("/home/james/stacklabs/dna/vault/notes/*_onboarding.md"):
        bp = parse_blueprint(filepath)
        if bp:
            blueprints.append(bp)

    print(f"Loaded {len(blueprints)} blueprints from disk.")
    blueprint_map = {bp["handle"].lower(): bp for bp in blueprints}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all personas in the database
    cur.execute("SELECT id, user_name, display_name, team, color, system_prompt, deep_lore FROM persona")
    persona_rows = cur.fetchall()
    print(f"Loaded {len(persona_rows)} persona records from database.")

    reconciled_blueprints = 0
    reconciled_audits = 0
    updated_records = []

    for row in persona_rows:
        sys_id = row["id"]
        user_name = row["user_name"]
        user_name_lower = user_name.lower()
        db_display_name = row["display_name"]
        db_team = row["team"]
        db_color = row["color"]
        prompt = row["system_prompt"] or ""
        lore = row["deep_lore"] or ""

        target_team = db_team
        target_display_name = db_display_name
        by_blueprint = False

        # 1. Check if we have a blueprint for this persona
        if user_name_lower in blueprint_map:
            bp = blueprint_map[user_name_lower]
            target_team = bp["team"].upper()
            target_display_name = bp["display_name"]
            by_blueprint = True
        else:
            # 2. If no blueprint, audit the prompt and deep lore
            detected = detect_team_from_content(user_name, db_display_name, prompt, lore)
            if detected:
                target_team = detected

        # Normalize WSH / WAS
        if target_team == "WAS":
            target_team = "WSH"

        target_color = TEAM_COLORS.get(target_team, "#0d9488")

        # Check if anything needs updating
        if (db_team != target_team) or (db_display_name != target_display_name) or (db_color != target_color):
            print(f"Reconciling @{user_name}:")
            if db_team != target_team:
                print(f"  Team: {db_team} -> {target_team}")
            if db_display_name != target_display_name:
                print(f"  Name: {db_display_name} -> {target_display_name}")
            if db_color != target_color:
                print(f"  Color: {db_color} -> {target_color}")

            # Update persona table
            cur.execute("""
                UPDATE persona SET 
                    display_name = ?,
                    team = ?,
                    color = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (target_display_name, target_team, target_color, sys_id))

            # Update sys_user table
            name_parts = target_display_name.split(" ")
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            cur.execute("""
                UPDATE sys_user SET
                    display_name = ?,
                    first_name = ?,
                    last_name = ?,
                    department = ?,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE LOWER(user_name) = ? OR sys_id = ?
            """, (target_display_name, first_name, last_name, target_team, user_name_lower, sys_id))

            # Update cmdb_ci table
            cur.execute("""
                UPDATE cmdb_ci SET
                    name = ?,
                    assigned_to = ?,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (user_name_lower, target_team, sys_id))

            if by_blueprint:
                reconciled_blueprints += 1
            else:
                reconciled_audits += 1

            updated_records.append({
                "handle": user_name,
                "old_team": db_team,
                "new_team": target_team,
                "old_name": db_display_name,
                "new_name": target_display_name,
                "source": "Blueprint" if by_blueprint else "Content Audit"
            })

    # Perform personnel swap in Game Room 823614: swap bartmans_ghost (54eda5e3bb7449d6b73369b1ba725eaf) for bartman (05d6724056cd4c91b60909af8b70d28b)
    cur.execute("""
        SELECT sys_id FROM m2m_persona_room 
        WHERE room = '823614' AND persona = '54eda5e3bb7449d6b73369b1ba725eaf'
    """)
    swap_row = cur.fetchone()
    
    swapped = False
    if swap_row:
        print("Performing personnel swap in Game Room 823614: swapping bartmans_ghost for bartman...")
        cur.execute("""
            UPDATE m2m_persona_room 
            SET persona = '05d6724056cd4c91b60909af8b70d28b', sys_updated_on = CURRENT_TIMESTAMP
            WHERE room = '823614' AND persona = '54eda5e3bb7449d6b73369b1ba725eaf'
        """)
        swapped = True
        print("Swap completed successfully.")
    else:
        # Check if bartman is already in the room
        cur.execute("""
            SELECT sys_id FROM m2m_persona_room 
            WHERE room = '823614' AND persona = '05d6724056cd4c91b60909af8b70d28b'
        """)
        if cur.fetchone():
            print("bartman is already in Game Room 823614.")
        else:
            print("Warning: Could not find bartmans_ghost in Game Room 823614 to perform swap.")

    conn.commit()
    conn.close()

    print("\nReconciliation Summary:")
    print(f"  Reconciled via blueprints: {reconciled_blueprints}")
    print(f"  Reconciled via content audits: {reconciled_audits}")
    print(f"  Game Room 823614 Swap: {'SUCCESS' if swapped else 'SKIPPED/NO-OP'}")
    print(f"  Total records updated: {len(updated_records)}")

if __name__ == "__main__":
    main()
