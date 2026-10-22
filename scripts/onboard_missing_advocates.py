#!/usr/bin/env python3
import os
import re
import sys
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
EXPORT_PATH = "/home/james/stacklabs/dna/vault/personas/sovereign_personas_export_02.md"

# Team Colors mapping
TEAM_COLORS = {
    "SPITESLICE": "#f43f5e", # rose
    "CARYGRANTINVESTIGATIONS": "#3b82f6", # blue
    "GLOBAL": "#0d9488"
}

def parse_advocate(handle, section_text):
    print(f"\nProcessing advocate: {handle}")
    
    # Team
    team = "GLOBAL"
    team_match = re.search(r"\*\*Team:\*\*\s*(.+)", section_text)
    if team_match:
        team = team_match.group(1).strip().upper()
        
    # Cadence
    cadence = "pacer"
    cadence_match = re.search(r"\*\*Cadence:\*\*\s*(.+)", section_text)
    if cadence_match:
        cadence = cadence_match.group(1).strip()
        
    # Boggs Reactivity
    boggs_reactivity = 3
    boggs_match = re.search(r"\*\*Boggs Reactivity:\*\*\s*(\d+)", section_text)
    if boggs_match:
        boggs_reactivity = int(boggs_match.group(1).strip())
        
    # System Prompt (in triple backticks)
    system_prompt = ""
    prompt_match = re.search(r"\*\*System Prompt:\*\*\s*\n```\n(.*?)\n```", section_text, re.DOTALL)
    if not prompt_match:
        prompt_match = re.search(r"\*\*System Prompt:\*\*\s*```\n(.*?)\n```", section_text, re.DOTALL)
    if prompt_match:
        system_prompt = prompt_match.group(1).strip()
    else:
        print(f"Warning: Could not parse system prompt for {handle}")

    # Deep Lore
    deep_lore = ""
    if system_prompt:
        lore_match = re.search(r"###\s*\**3\.\s*LORE KEYS.*?\n(.*?)(?=\n###\s*\**4\.|\Z)", system_prompt, re.DOTALL | re.IGNORECASE)
        if lore_match:
            deep_lore = lore_match.group(1).strip()
        else:
            deep_lore = "Dossier available in system prompt."

    # Bio
    bio = ""
    if system_prompt:
        bio_match = re.search(r"\*\*Bio \(max 160 chars\):\*\*\s*\n([^\n]+)", system_prompt, re.IGNORECASE)
        if not bio_match:
            bio_match = re.search(r"###\s*\**2\.\s*PERSONALITY PROFILE.*?\n(.*?)(?=\n###|\Z)", system_prompt, re.DOTALL | re.IGNORECASE)
        if bio_match:
            bio = bio_match.group(1).strip()[:160]
            
    if not bio:
        bio = f"Brand Advocate for {team}."

    # Display Name
    display_name = handle.replace("_", " ").title()
    if handle == "warden_barb":
        display_name = "Barb the Warden"
    elif handle == "cary_sterling":
        display_name = "Cary Sterling"
    elif handle == "vesper_vance":
        display_name = "Vesper Vance"

    return {
        "handle": handle,
        "team": team,
        "cadence": cadence,
        "boggs_reactivity": boggs_reactivity,
        "system_prompt": system_prompt,
        "deep_lore": deep_lore,
        "bio": bio,
        "display_name": display_name
    }

def main():
    print("Parsing export file...")
    if not os.path.exists(EXPORT_PATH):
        print(f"Error: Export file not found at {EXPORT_PATH}")
        sys.exit(1)

    with open(EXPORT_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    sections = {}
    current_handle = None
    current_lines = []

    for line in lines:
        m = re.match(r"^## ([a-z0-9_]+)$", line.strip())
        if m:
            if current_handle in ["warden_barb", "cary_sterling", "vesper_vance"]:
                sections[current_handle] = "".join(current_lines)
            current_handle = m.group(1)
            current_lines = []
        current_lines.append(line)

    if current_handle in ["warden_barb", "cary_sterling", "vesper_vance"]:
        sections[current_handle] = "".join(current_lines)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    for handle in ["warden_barb", "cary_sterling", "vesper_vance"]:
        section_text = sections.get(handle)
        if not section_text:
            print(f"Error: Section for {handle} not found in parsed lines.")
            continue
            
        data = parse_advocate(handle, section_text)
        
        # Write canonical blueprint file
        blueprint_dir = "/home/james/stacklabs/dna/personas"
        os.makedirs(blueprint_dir, exist_ok=True)
        blueprint_path = os.path.join(blueprint_dir, f"{handle}_onboarding.md")
        
        email_alias = f"sovereign.fanstack+{handle}@gmail.com"
        avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
        
        blueprint_content = f"""# X/Twitter Onboarding Blueprint: `{handle}`

## 👤 Profile Details

**X Handle:** `@{handle}`
**Email Alias:** `{email_alias}`
**Display Name:** {data['display_name']}
**Team:** {data['team']}
**Location:** Smyrna Heights

**Bio (max 160 chars):** 
{data['bio']}

## 📖 Deep Lore
{data['deep_lore']}

# Style Profile
Tier: Standard

## 🖼️ Profile Pictures

**Avatar:**
{avatar_url}
"""
        with open(blueprint_path, "w", encoding="utf-8") as bf:
            bf.write(blueprint_content)
        print(f"✅ Saved blueprint to {blueprint_path}")

        # SQLite Database operations
        color = TEAM_COLORS.get(data["team"], "#0d9488")
        
        # Check if already exists in persona table
        cur.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
        row = cur.fetchone()
        
        u_deployment_zone = "global"
        if data["team"] == "SPITESLICE":
            u_deployment_zone = "SPITESLICE_ZONE"
        elif data["team"] == "CARYGRANTINVESTIGATIONS":
            u_deployment_zone = "CARYGRANT_ZONE"

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
                    cadence = ?,
                    boggs_level = ?,
                    behavior_notes = ?,
                    u_deployment_zone = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (data["display_name"], data["team"], data["system_prompt"], avatar_url, color, data["deep_lore"], email_alias, data["cadence"], data["boggs_reactivity"], data["bio"], u_deployment_zone, sys_id))
        else:
            sys_id = uuid.uuid4().hex
            print(f"Inserting new record in persona table with ID: {sys_id}")
            cur.execute("""
                INSERT INTO persona (
                    id, user_name, display_name, team, system_prompt, boggs_level, 
                    avatar_url, color, cadence, deep_lore, email_alias,
                    u_visual_style, created_at, u_deployment_zone, behavior_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'style_felt', datetime('now'), ?, ?)
            """, (sys_id, handle, data["display_name"], data["team"], data["system_prompt"], data["boggs_reactivity"], avatar_url, color, data["cadence"], data["deep_lore"], email_alias, u_deployment_zone, data["bio"]))

        # Split name into first and last
        name_parts = data["display_name"].split(" ")
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        # Check/insert/update sys_user
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

        # Check/insert/update cmdb_ci
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

        # Check/insert/update cmdb_ci_ai_persona
        cur.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
        ap_row = cur.fetchone()
        if ap_row:
            print(f"Updating cmdb_ci_ai_persona with ID: {sys_id}")
            cur.execute("""
                UPDATE cmdb_ci_ai_persona SET
                    u_system_prompt = ?,
                    u_deep_lore = ?,
                    u_deployment_zone = ?,
                    u_cadence = ?
                WHERE sys_id = ?
            """, (data["system_prompt"], data["deep_lore"], u_deployment_zone, data["cadence"], sys_id))
        else:
            print(f"Inserting into cmdb_ci_ai_persona with ID: {sys_id}")
            cur.execute("""
                INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore)
                VALUES (?, 'medium', ?, ?, ?, ?)
            """, (sys_id, data["system_prompt"], u_deployment_zone, data["cadence"], data["deep_lore"]))

    con.commit()
    con.close()
    print("🏆 Successfully completed all database advocate ingestions.")

if __name__ == "__main__":
    main()
