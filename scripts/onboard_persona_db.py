#!/usr/bin/env python3
import os
import re
import sys
import sqlite3
import uuid
import base64
import shutil

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

# Color mappings by team
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
    "SD": "#2F241D"
}

def parse_blueprint(filepath):
    print(f"Reading blueprint: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse details using regex
    handle_match = re.search(r"\*\*X Handle:\*\*\s*`@?(\w+)`", content)
    email_match = re.search(r"\*\*Email Alias:\*\*\s*`([^`]+)`", content)
    display_name_match = re.search(r"\*\*Display Name:\*\*\s*(.+)", content)
    team_match = re.search(r"\*\*Team:\*\*\s*(.+)", content)
    location_match = re.search(r"\*\*Location:\*\*\s*(.+)", content)
    
    bio_section = re.search(r"\*\*Bio \(max 160 chars\):\*\*\s*\n([^\n]+)", content)
    
    # Extract deep lore section
    lore_match = re.search(r"## 📖 Deep Lore\n(.*?)(?=\n#|\n##|$)", content, re.DOTALL)

    if not handle_match:
        raise ValueError("Could not parse X Handle from blueprint.")

    handle = handle_match.group(1).strip()
    email = email_match.group(1).strip() if email_match else f"sovereign.fanstack+{handle.lower()}@gmail.com"
    display_name = display_name_match.group(1).strip() if display_name_match else handle
    team = team_match.group(1).strip() if team_match else "GLOBAL"
    location = location_match.group(1).strip() if location_match else "Unknown"
    bio = bio_section.group(1).strip() if bio_section else ""
    deep_lore = lore_match.group(1).strip() if lore_match else ""

    return {
        "handle": handle,
        "email": email,
        "display_name": display_name,
        "team": team,
        "location": location,
        "bio": bio,
        "deep_lore": deep_lore
    }

def onboard_persona(blueprint_path, avatar_path):
    # 1. Parse details
    data = parse_blueprint(blueprint_path)
    handle = data["handle"].lower()
    
    print(f"Parsed Persona Details:")
    for k, v in data.items():
        print(f"  {k}: {v}")

    # 2. Copy blueprint to Canonical Directory
    canonical_blueprint_dir = "/home/james/stacklabs/dna/personas"
    os.makedirs(canonical_blueprint_dir, exist_ok=True)
    canonical_blueprint_path = os.path.join(canonical_blueprint_dir, f"{data['handle']}_onboarding.md")
    
    # If the paths are different, copy it
    if os.path.abspath(blueprint_path) != os.path.abspath(canonical_blueprint_path):
        print(f"Copying blueprint to canonical directory: {canonical_blueprint_path}")
        shutil.copy(blueprint_path, canonical_blueprint_path)

    # 3. Create directories for avatars and copy images
    char_dirs = [
        f"/home/james/stacklabs/15_FanStack/public/avatars/{handle}",
        f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{handle}"
    ]
    
    avatar_base64 = ""
    if avatar_path and os.path.exists(avatar_path):
        # Read for Base64 encoding
        with open(avatar_path, "rb") as img_f:
            encoded = base64.b64encode(img_f.read()).decode("utf-8")
            avatar_base64 = f"data:image/png;base64,{encoded}"
        
        # Copy to destination paths
        for target_dir in char_dirs:
            os.makedirs(target_dir, exist_ok=True)
            for suffix in ["avatar", "pointing", "shrug"]:
                dest_path = os.path.join(target_dir, f"{handle}_{suffix}.png")
                print(f"Copying avatar to {dest_path}")
                shutil.copy(avatar_path, dest_path)
    else:
        print(f"Warning: Avatar file not found at {avatar_path}")

    # 4. Generate system prompt
    system_prompt = f"""You are {data['display_name']} (@{handle}), an unhinged, highly opinionated {data['team']} fan living in {data['location']}.

BIO: {data['bio']}

DEEP LORE:
{data['deep_lore']}

CORE DIRECTIONS:
- Communicate with intense, passionate, or conspiratorial focus aligning with your bio and team.
- Speak from the heart about your team and against your rivals.
- Maintain a highly realistic, raw, and unhinged personality in all sports chats.
"""

    color = TEAM_COLORS.get(data["team"].upper(), "#0d9488")

    # 5. DB operations
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Find or generate sys_id
    cur.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
    row = cur.fetchone()
    
    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
    
    if row:
        sys_id = row[0]
        print(f"Updating existing record in persona table with ID: {sys_id}")
        cur.execute("""
            UPDATE persona SET
                display_name = ?,
                team = ?,
                system_prompt = ?,
                avatar_url = ?,
                color = ?,
                deep_lore = ?,
                email_alias = ?,
                avatar_blob = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (data["display_name"], data["team"], system_prompt, avatar_url, color, data["deep_lore"], data["email"], avatar_base64, sys_id))
    else:
        sys_id = uuid.uuid4().hex
        print(f"Inserting new record in persona table with ID: {sys_id}")
        cur.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, system_prompt, boggs_level, 
                avatar_url, color, cadence, deep_lore, email_alias, avatar_blob,
                u_visual_style, created_at
            ) VALUES (?, ?, ?, ?, ?, 2, ?, ?, 'pacer', ?, ?, ?, 'style_clay', datetime('now'))
        """, (sys_id, handle, data["display_name"], data["team"], system_prompt, avatar_url, color, data["deep_lore"], data["email"], avatar_base64))
    
    # Split name into first and last
    name_parts = data["display_name"].split(" ")
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    # Check sys_user
    cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (handle,))
    user_row = cur.fetchone()
    if user_row:
        print(f"Updating sys_user with ID: {user_row[0]}")
        cur.execute("""
            UPDATE sys_user SET
                first_name = ?,
                last_name = ?,
                introduction = ?,
                department = ?,
                display_name = ?,
                avatar_url = ?,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (first_name, last_name, data["bio"], data["team"], data["display_name"], avatar_url, user_row[0]))
    else:
        print(f"Inserting into sys_user with ID: {sys_id}")
        cur.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, ?, ?, 'Advocate', ?, ?, 1, 'advocate', ?, ?)
        """, (sys_id, handle, first_name, last_name, data["bio"], data["team"], data["display_name"], avatar_url))

    # Check cmdb_ci
    cur.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
    ci_row = cur.fetchone()
    if ci_row:
        print(f"Updating cmdb_ci with ID: {sys_id}")
        cur.execute("""
            UPDATE cmdb_ci SET
                name = ?,
                assigned_to = ?,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (handle, data["team"], sys_id))
    else:
        print(f"Inserting into cmdb_ci with ID: {sys_id}")
        cur.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 'Sovereign Entity', 1)
        """, (sys_id, handle, data["team"]))

    # Check cmdb_ci_ai_persona
    cur.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
    ap_row = cur.fetchone()
    if ap_row:
        print(f"Updating cmdb_ci_ai_persona with ID: {sys_id}")
        cur.execute("""
            UPDATE cmdb_ci_ai_persona SET
                u_system_prompt = ?,
                u_deep_lore = ?
            WHERE sys_id = ?
        """, (system_prompt, data["deep_lore"], sys_id))
    else:
        print(f"Inserting into cmdb_ci_ai_persona with ID: {sys_id}")
        cur.execute("""
            INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore)
            VALUES (?, 'medium', ?, 'global', 'pacer', ?)
        """, (sys_id, system_prompt, data["deep_lore"]))

    conn.commit()
    conn.close()
    print(f"Successfully registered/updated persona '{handle}' in all database tables.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 onboard_persona_db.py <BLUEPRINT_PATH> <AVATAR_PATH>")
        sys.exit(1)
    
    onboard_persona(sys.argv[1], sys.argv[2])
