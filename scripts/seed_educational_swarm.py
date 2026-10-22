#!/usr/bin/env python3
import os
import re
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
EXPORT_PATH = "/home/james/stacklabs/dna/vault/personas/sovereign_personas_export_02.md"

TARGET_HANDLES = {
    "captain_atlas_guide": "Captain Atlas",
    "celeste_dreamweaver": "Celeste",
    "flora_fern_eco": "Dr. Flora Fern",
    "melody_hearth_fairy": "Melody the Fairy",
    "pip_gears_math": "Pip the Squirrel",
    "scribble_quill_explorer": "Scribble & Quill"
}

def clean_section_text(text):
    text = text.strip()
    if text.startswith("```"):
        # Strip code block fences
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text

def main():
    print(f"Reading export file: {EXPORT_PATH}...")
    if not os.path.exists(EXPORT_PATH):
        print(f"Error: export file not found at {EXPORT_PATH}")
        return

    with open(EXPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by ## at the start of a line
    sections = re.split(r"\n## ", content)
    
    parsed_personas = {}

    for sec in sections:
        lines = sec.split("\n")
        if not lines:
            continue
        uname = lines[0].strip()
        if uname in TARGET_HANDLES:
            print(f"Found match: {uname}")
            sec_text = "\n".join(lines[1:])
            
            # Parse fields
            team_match = re.search(r"\*\*Team:\*\*\s*(.*)", sec_text)
            team = team_match.group(1).strip() if team_match else "EDUCATIONALSWARM"
            
            cadence_match = re.search(r"\*\*Cadence:\*\*\s*(.*)", sec_text)
            cadence = cadence_match.group(1).strip() if cadence_match else "pacer"
            
            boggs_match = re.search(r"\*\*Boggs Reactivity:\*\*\s*(.*)", sec_text)
            boggs_level = int(boggs_match.group(1).strip()) if boggs_match else 3
            
            # System Prompt
            system_prompt = ""
            sys_match = re.search(r"\*\*System Prompt:\*\*\s*\n(.*?)(?=\n\*\*|$)", sec_text, re.DOTALL)
            if sys_match:
                system_prompt = clean_section_text(sys_match.group(1))
            
            # Behavior Notes
            behavior_notes = ""
            beh_match = re.search(r"\*\*Behavior Notes:\*\*\s*\n(.*?)(?=\n\*\*|$)", sec_text, re.DOTALL)
            if beh_match:
                behavior_notes = clean_section_text(beh_match.group(1))
                
            # Deep Lore
            deep_lore = ""
            lore_match = re.search(r"\*\*Deep Lore:\*\*\s*\n(.*?)(?=\n\*\*|$)", sec_text, re.DOTALL)
            if lore_match:
                deep_lore = clean_section_text(lore_match.group(1))
                
            # Governance
            governance = ""
            gov_match = re.search(r"\*\*Governance:\*\*\s*\n(.*?)(?=\n\*\*|$)", sec_text, re.DOTALL)
            if gov_match:
                governance = clean_section_text(gov_match.group(1))
                
            parsed_personas[uname] = {
                "display_name": TARGET_HANDLES[uname],
                "team": team,
                "cadence": cadence,
                "boggs_level": boggs_level,
                "system_prompt": system_prompt,
                "behavior_notes": behavior_notes,
                "deep_lore": deep_lore,
                "governance": governance
            }

    print(f"Syncing to SQLite database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for uname, data in parsed_personas.items():
        # Check if already exists
        cursor.execute("SELECT id FROM persona WHERE user_name=?", (uname,))
        row = cursor.fetchone()
        
        # Determine color for this persona
        # Let's assign unique aesthetic colors
        colors = {
            "captain_atlas_guide": "#0ea5e9", # Sky blue
            "celeste_dreamweaver": "#a855f7", # Purple
            "flora_fern_eco": "#22c55e", # Green
            "melody_hearth_fairy": "#ec4899", # Pink
            "pip_gears_math": "#eab308", # Yellow
            "scribble_quill_explorer": "#f97316" # Orange
        }
        color = colors.get(uname, "#0ea5e9")
        
        avatar_url = f"/avatars/{uname}/{uname}_avatar.png"
        
        if row:
            print(f"Updating persona @{uname}...")
            cursor.execute("""
                UPDATE persona
                SET display_name=?, team=?, system_prompt=?, boggs_level=?, cadence=?, deep_lore=?, behavior_notes=?, governance=?, color=?, avatar_url=?
                WHERE user_name=?
            """, (data["display_name"], data["team"], data["system_prompt"], data["boggs_level"], data["cadence"], data["deep_lore"], data["behavior_notes"], data["governance"], color, avatar_url, uname))
        else:
            print(f"Inserting new persona @{uname}...")
            sys_id = uuid.uuid4().hex
            cursor.execute("""
                INSERT INTO persona (id, user_name, display_name, team, system_prompt, boggs_level, cadence, deep_lore, behavior_notes, governance, color, avatar_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sys_id, uname, data["display_name"], data["team"], data["system_prompt"], data["boggs_level"], data["cadence"], data["deep_lore"], data["behavior_notes"], data["governance"], color, avatar_url))
            
    conn.commit()
    conn.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    main()
