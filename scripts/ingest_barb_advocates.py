#!/usr/bin/env python3
import os
import re
import sys
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
EXPORT_PATH = "/home/james/sovereign_inbox/pilot_drops/Barb/barbs_sovereign_advocates_export.md"

def parse_advocate_section(content, handle):
    pattern = r"\n## " + re.escape(handle) + r"\b"
    match = re.search(pattern, content)
    if not match:
        return None
        
    start_idx = match.start()
    # Find next top-level h2 header
    # A top-level h2 is ## followed by space and one of the known handles
    next_header_match = re.search(r"\n## (barb_the_founder|barbara_ci)\b", content[start_idx + 4:])
    if next_header_match:
        end_idx = start_idx + 4 + next_header_match.start()
    else:
        end_idx = len(content)
        
    return content[start_idx:end_idx]

def main():
    print("Ingesting Barb's AI Advocates...")
    if not os.path.exists(EXPORT_PATH):
        print(f"Error: Export file not found at {EXPORT_PATH}")
        sys.exit(1)

    with open(EXPORT_PATH, "r", encoding="utf-8") as f:
        content = "\n" + f.read()

    handles = ["barb_the_founder", "barbara_ci"]
    
    for handle in handles:
        section = parse_advocate_section(content, handle)
        if not section:
            print(f"Advocate {handle} not found in export.")
            continue
            
        print(f"\nProcessing advocate: {handle}")
        lines = section.strip().split("\n")
        
        # Extract fields
        team = "global"
        cadence = "pacer"
        boggs_reactivity = 3
        system_prompt = ""
        behavior_notes = ""
        deep_lore = ""
        governance = ""
        avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={handle}&backgroundColor=0f172a&textColor=ffffff"

        section_text = section
        
        team_match = re.search(r"\*\*Team:\*\*\s*(.+)", section_text)
        if team_match:
            team = team_match.group(1).strip()
            
        cadence_match = re.search(r"\*\*Cadence:\*\*\s*(.+)", section_text)
        if cadence_match:
            cadence = cadence_match.group(1).strip()

        boggs_match = re.search(r"\*\*Boggs Reactivity:\*\*\s*(\d+)", section_text)
        if boggs_match:
            boggs_reactivity = int(boggs_match.group(1).strip())

        prompt_match = re.search(r"\*\*System Prompt:\*\*\s*\n```\n(.*?)\n```", section_text, re.DOTALL)
        if prompt_match:
            system_prompt = prompt_match.group(1).strip()
            
        behavior_match = re.search(r"\*\*Behavior Notes:\*\*\s*\n(.*?)(?=\n\*\*|\Z)", section_text, re.DOTALL)
        if behavior_match:
            behavior_notes = behavior_match.group(1).strip()
            
        lore_match = re.search(r"\*\*Deep Lore:\*\*\s*\n(.*?)(?=\n\*\*|\Z)", section_text, re.DOTALL)
        if lore_match:
            deep_lore = lore_match.group(1).strip()
            
        gov_match = re.search(r"\*\*Governance:\*\*\s*\n(.*?)(?=\n\*\*|\Z)", section_text, re.DOTALL)
        if gov_match:
            governance = gov_match.group(1).strip()

        avatar_url_match = re.search(r"!\[.*?\]\((.*?)\)", section_text)
        if avatar_url_match:
            avatar_url = avatar_url_match.group(1).strip()

        display_name = handle.replace("_", " ").title()
        if handle == "barb_the_founder":
            display_name = "Barb the Founder"
        elif handle == "barbara_ci":
            display_name = "barbara"

        print(f"Parsed fields:")
        print(f"  Display Name: {display_name}")
        print(f"  Team: {team}")
        print(f"  Cadence: {cadence}")
        print(f"  Boggs: {boggs_reactivity}")
        print(f"  Avatar URL: {avatar_url}")
        print(f"  Deep Lore Length: {len(deep_lore)}")

        # Write onboarding blueprint file
        blueprint_dir = "/home/james/stacklabs/dna/personas"
        os.makedirs(blueprint_dir, exist_ok=True)
        blueprint_path = os.path.join(blueprint_dir, f"{handle}_onboarding.md")
        
        email_alias = f"sovereign.fanstack+{handle}@gmail.com"
        
        blueprint_content = f"""# X/Twitter Onboarding Blueprint: `{handle}`

## 👤 Profile Details

**X Handle:** `@{handle}`
**Email Alias:** `{email_alias}`
**Display Name:** {display_name}
**Team:** {team}
**Location:** Smyrna Heights

**Bio (max 160 chars):** 
{behavior_notes[:160] if behavior_notes else "Advocate for Smyrna Heights."}

## 📖 Deep Lore
{deep_lore}

# Style Profile
Tier: Standard

## 🖼️ Profile Pictures

**Avatar:**
{avatar_url}
"""
        with open(blueprint_path, "w", encoding="utf-8") as bf:
            bf.write(blueprint_content)
        print(f"Saved blueprint to {blueprint_path}")

        # DB operations
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Check if already exists in persona table
        cur.execute("SELECT id, u_deployment_zone FROM persona WHERE user_name = ?", (handle,))
        row = cur.fetchone()
        
        u_deployment_zone = "global"
        if handle == "barb_the_founder":
            u_deployment_zone = "WILDPAWSCANVAS_SIM_001"
        elif handle == "barbara_ci":
            u_deployment_zone = "BENCHED"
            
        if row:
            sys_id = row[0]
            if row[1]:
                u_deployment_zone = row[1]
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
                    governance = ?,
                    u_deployment_zone = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (display_name, team, system_prompt, avatar_url, "#0d9488", deep_lore, email_alias, cadence, boggs_reactivity, behavior_notes, governance, u_deployment_zone, sys_id))
        else:
            sys_id = uuid.uuid4().hex
            print(f"Inserting new record in persona table with ID: {sys_id}")
            cur.execute("""
                INSERT INTO persona (
                    id, user_name, display_name, team, system_prompt, boggs_level, 
                    avatar_url, color, cadence, deep_lore, email_alias,
                    u_visual_style, created_at, u_deployment_zone, behavior_notes, governance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, '#0d9488', ?, ?, ?, 'style_felt', datetime('now'), ?, ?, ?)
            """, (sys_id, handle, display_name, team, system_prompt, boggs_reactivity, avatar_url, cadence, deep_lore, email_alias, u_deployment_zone, behavior_notes, governance))

        # Split name into first and last
        name_parts = display_name.split(" ")
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
            """, (first_name, last_name, behavior_notes[:160], team, display_name, avatar_url, user_row[0]))
        else:
            print(f"Inserting into sys_user with ID: {sys_id}")
            cur.execute("""
                INSERT INTO sys_user (
                    sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
                ) VALUES (?, ?, ?, ?, 'Advocate', ?, ?, 1, 'advocate', ?, ?)
            """, (sys_id, handle, first_name, last_name, behavior_notes[:160], team, display_name, avatar_url))

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
            """, (handle, team, sys_id))
        else:
            print(f"Inserting into cmdb_ci with ID: {sys_id}")
            cur.execute("""
                INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
                VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 'Sovereign Entity', 1)
            """, (sys_id, handle, team))

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
                    u_cadence = ?,
                    u_boggs_reactivity = ?
                WHERE sys_id = ?
            """, (system_prompt, deep_lore, u_deployment_zone, cadence, boggs_reactivity, sys_id))
        else:
            print(f"Inserting into cmdb_ci_ai_persona with ID: {sys_id}")
            cur.execute("""
                INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sys_id, boggs_reactivity, system_prompt, u_deployment_zone, cadence, deep_lore))

        conn.commit()
        conn.close()
        print(f"Successfully registered '{handle}' in all tables.")

if __name__ == "__main__":
    main()
