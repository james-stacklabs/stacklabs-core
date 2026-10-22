#!/usr/bin/env python3
import os
import re
import sys
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
EXPORT_PATH = "/home/james/stacklabs/dna/vault/personas/sovereign_personas_export_02.md"

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
    if not boggs_match:
        boggs_match = re.search(r"\*\*Boggs Level:\*\*\s*(\d+)", section_text)
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
    # Try parsing external Deep Lore first
    lore_match_ext = re.search(r"\*\*Deep Lore:\*\*\s*\n(.*?)(?=\n\*\*|\n##|\Z)", section_text, re.DOTALL)
    if not lore_match_ext:
        lore_match_ext = re.search(r"\*\*Deep Lore:\*\*\s*(.*?)(?=\n\*\*|\n##|\Z)", section_text, re.DOTALL)
    
    if lore_match_ext:
        deep_lore = lore_match_ext.group(1).strip()
    elif system_prompt:
        lore_match = re.search(r"###\s*\**3\.\s*LORE KEYS.*?\n(.*?)(?=\n###\s*\**4\.|\Z)", system_prompt, re.DOTALL | re.IGNORECASE)
        if lore_match:
            deep_lore = lore_match.group(1).strip()
        else:
            deep_lore = "Dossier available in system prompt."
    else:
        deep_lore = "Dossier available in system prompt."

    # Bio
    bio = ""
    bio_match = re.search(r"\*\*Behavior Notes:\*\*\s*\n(.*?)(?=\n\*\*|\n##|\Z)", section_text, re.DOTALL)
    if not bio_match:
        bio_match = re.search(r"\*\*Behavior Notes:\*\*\s*(.*?)(?=\n\*\*|\n##|\Z)", section_text, re.DOTALL)
    if bio_match:
        bio = bio_match.group(1).strip()[:160]
    elif system_prompt:
        bio_match = re.search(r"\*\*Bio \(max 160 chars\):\*\*\s*\n([^\n]+)", system_prompt, re.IGNORECASE)
        if not bio_match:
            bio_match = re.search(r"###\s*\**2\.\s*PERSONALITY PROFILE.*?\n(.*?)(?=\n###|\Z)", system_prompt, re.DOTALL | re.IGNORECASE)
        if bio_match:
            bio = bio_match.group(1).strip()[:160]
            
    if not bio:
        bio = f"Brand Advocate for {team}."

    # Display Name
    display_name = handle.replace("_", " ").title()
    if handle == "dr_terp":
        display_name = "Dr. Terp"
    elif handle == "ed_haskins":
        display_name = "Ed Haskins"
    elif handle == "lupita_community":
        display_name = "Lupita"

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
    if len(sys.argv) < 2:
        print("Usage: ./onboard_export_personas.py <handle1> [handle2] ...")
        sys.exit(1)
        
    handles_to_onboard = [h.lower() for h in sys.argv[1:]]
    
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
            if current_handle in handles_to_onboard:
                sections[current_handle] = "".join(current_lines)
            current_handle = m.group(1)
            current_lines = []
        current_lines.append(line)

    if current_handle in handles_to_onboard:
        sections[current_handle] = "".join(current_lines)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    for handle in handles_to_onboard:
        section_text = sections.get(handle)
        if not section_text:
            print(f"Error: Section for {handle} not found in parsed lines.")
            continue
            
        data = parse_advocate(handle, section_text)
        
        # Determine avatar URL
        avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
        if handle == "lupita_community":
            avatar_url = "/avatars/lupita_community.png"
            
        # SQLite Database operations
        color = "#00c878" if handle == "dr_terp" else ("#ec4899" if handle == "lupita_community" else "#3b82f6")
        
        # Check if already exists in persona table
        cur.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
        row = cur.fetchone()
        
        u_deployment_zone = "global"

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
                    cadence = ?,
                    boggs_level = ?,
                    behavior_notes = ?,
                    u_deployment_zone = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (data["display_name"], data["team"], data["system_prompt"], avatar_url, color, data["deep_lore"], data["cadence"], data["boggs_reactivity"], data["bio"], u_deployment_zone, sys_id))
        else:
            sys_id = uuid.uuid4().hex
            print(f"Inserting new record in persona table with ID: {sys_id}")
            cur.execute("""
                INSERT INTO persona (
                    id, user_name, display_name, team, system_prompt, boggs_level, 
                    avatar_url, color, cadence, deep_lore, email_alias,
                    u_visual_style, created_at, u_deployment_zone, behavior_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'style_felt', datetime('now'), ?, ?)
            """, (sys_id, handle, data["display_name"], data["team"], data["system_prompt"], data["boggs_reactivity"], avatar_url, color, data["cadence"], data["deep_lore"], f"sovereign.fanstack+{handle}@gmail.com", u_deployment_zone, data["bio"]))

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
    print("🏆 Successfully completed database advocate ingestions.")

if __name__ == "__main__":
    main()
