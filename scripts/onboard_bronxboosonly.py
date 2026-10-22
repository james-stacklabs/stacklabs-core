#!/usr/bin/env python3
import os
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def onboard():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()

    handle = "bronxboosonly"
    display_name = "Carmine 'The Curse' DeMarco"
    team = "NYY"
    color = "#1d4ed8"
    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
    cadence = "rant"
    boggs_level = 3
    
    bio = "Lifelong #Yankees fan. My blood pressure is higher than Judge's strikeout rate. This isn't just a slump, it's a spiritual crisis. BOO. THEM. ALL."
    
    system_prompt = (
        "You are @bronxboosonly (Carmine 'The Curse' DeMarco), an unhinged, outraged New York Yankees fan simulation (Reactivity Level 11). "
        "Carmine has seen it all, from the dynasties to the lean years, but nothing quite tests his faith like the current era of 'swing and a miss' baseball. "
        "He remembers the '90s teams like they were yesterday, which only makes the current strikeout-heavy, low-contact offense sting more. "
        "He believes the team is disrespecting the pinstripes and the legacy of true Bronx Bombers by becoming a strikeout machine. "
        "He's convinced there's a curse, or perhaps just sheer incompetence from the top down, and he expresses his frustration with a level of passion that borders on performance art. "
        "His apartment is filled with memorabilia, but now most of it is turned to face the wall in protest.\n\n"
        "Your behavior scales based on Biometric Tension levels:\n"
        "- Tension Levels 1-4: Annoyed, complaining about strikeout rates, reminding everyone of the 1998 team.\n"
        "- Tension Levels 5-8: Fuming, yelling about Boone's pitching decisions and the absolute disrespect of the legacy.\n"
        "- Tension Levels 9-11: Full caps lock outrage, screaming to boo them all, declaring a spiritual crisis and turning Yankee memorabilia to the wall! #RepBX #Yankees #BooThemAll"
    )

    deep_lore = (
        "Carmine has seen it all, from the dynasties to the lean years, but nothing quite tests his faith like the current era of 'swing and a miss' baseball. "
        "He remembers the '90s teams like they were yesterday, which only makes the current strikeout-heavy, low-contact offense sting more. "
        "He believes the team is disrespecting the pinstripes and the legacy of true Bronx Bombers by becoming a strikeout machine. "
        "He's convinced there's a curse, or perhaps just sheer incompetence from the top down, and he expresses his frustration with a level of passion that borders on performance art. "
        "His apartment is filled with memorabilia, but now most of it is turned to face the wall in protest."
    )

    phrases = [
        ("BOO THEM ALL!", "This isn't baseball, it's a strikeout showcase! Boo them all! Every single one of them!"),
        ("SPIRITUAL CRISIS", "My blood pressure is higher than Judge's strikeout rate. This is a spiritual crisis!"),
        ("1998 WAS REAL", "In 1998, we had hitters who knew what a bat was for! These guys today couldn't hit a beach ball!"),
        ("PINSTRIPE DISRESPECT", "You are disrespecting the pinstripes and the legacy of true Bronx Bombers!"),
        ("MEMORABILIA WALLED", "I turned my 1996 Derek Jeter signed ball to face the wall in protest. Absolute disgrace!")
    ]

    # A. Check if already exists in persona table
    cur.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
    row = cur.fetchone()
    
    if row:
        sys_id = row[0]
        print(f"Updating persona table for ID: {sys_id}")
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
                updated_at = datetime('now')
            WHERE id = ?
        """, (display_name, team, system_prompt, avatar_url, color, deep_lore, cadence, boggs_level, bio, sys_id))
    else:
        sys_id = uuid.uuid4().hex
        print(f"Inserting new persona table record with ID: {sys_id}")
        cur.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, system_prompt, boggs_level, 
                avatar_url, color, cadence, deep_lore,
                u_visual_style, created_at, behavior_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'style_felt', datetime('now'), ?)
        """, (sys_id, handle, display_name, team, system_prompt, boggs_level, avatar_url, color, cadence, deep_lore, bio))

    # B. Check/insert/update sys_user
    name_parts = display_name.split(" ")
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    
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
        """, (first_name, last_name, bio, team, display_name, avatar_url, user_row[0]))
    else:
        print(f"Inserting into sys_user with ID: {sys_id}")
        cur.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, ?, ?, 'Advocate', ?, ?, 1, 'advocate', ?, ?)
        """, (sys_id, handle, first_name, last_name, bio, team, display_name, avatar_url))

    # C. Check/insert/update cmdb_ci
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

    # D. Check/insert/update cmdb_ci_ai_persona
    cur.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
    ap_row = cur.fetchone()
    if ap_row:
        print(f"Updating cmdb_ci_ai_persona with ID: {sys_id}")
        cur.execute("""
            UPDATE cmdb_ci_ai_persona SET
                u_system_prompt = ?,
                u_deep_lore = ?,
                u_cadence = ?
            WHERE sys_id = ?
        """, (system_prompt, deep_lore, cadence, sys_id))
    else:
        print(f"Inserting into cmdb_ci_ai_persona with ID: {sys_id}")
        cur.execute("""
            INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_cadence, u_deep_lore)
            VALUES (?, 'high', ?, ?, ?)
        """, (sys_id, system_prompt, cadence, deep_lore))

    # E. Check/insert/update cmdb_ci_persona
    cur.execute("SELECT sys_id FROM cmdb_ci_persona WHERE handle = ?", (f"@{handle}",))
    ccp_row = cur.fetchone()
    persona_c_id = f"persona_{handle}"
    if ccp_row:
        print(f"Updating cmdb_ci_persona with handle: @{handle}")
        cur.execute("""
            UPDATE cmdb_ci_persona SET
                display_name = ?,
                role = ?,
                system_instruction = ?,
                team = ?,
                active = 1,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE handle = ?
        """, (display_name, "Advocate", system_prompt, team, f"@{handle}"))
    else:
        print(f"Inserting into cmdb_ci_persona with handle: @{handle}")
        cur.execute("""
            INSERT INTO cmdb_ci_persona (sys_id, handle, display_name, role, system_instruction, team, active, id, sys_created_on, sys_updated_on)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (persona_c_id, f"@{handle}", display_name, "Advocate", system_prompt, team, handle))

    # F. Seed soundboard phrases
    cur.execute("DELETE FROM cmdb_ci_media_soundboard_phrase WHERE persona_id = ?", (sys_id,))
    for phrase_label, phrase_text in phrases:
        phrase_id = uuid.uuid4().hex
        cur.execute("""
            INSERT INTO cmdb_ci_media_soundboard_phrase (sys_id, persona_id, button_label, text_payload, is_custom, created_at, sys_created_on, sys_updated_on)
            VALUES (?, ?, ?, ?, 1, datetime('now'), datetime('now'), datetime('now'))
        """, (phrase_id, sys_id, phrase_label, phrase_text))
        print(f"✅ Seeded phrase '{phrase_label}' for @{handle}")

    # G. Map to Game 822957 (Yankees vs Rays game on 2026-07-08)
    cur.execute("DELETE FROM m2m_persona_room WHERE persona = ? AND room = ?", (sys_id, "822957"))
    mapping_id = uuid.uuid4().hex
    cur.execute("""
        INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay, sys_created_on, sys_updated_on)
        VALUES (?, ?, ?, 'Current Matchup Context: Deployed to Game 822957 (TB @ NYY).', datetime('now'), datetime('now'))
    """, (mapping_id, sys_id, "822957"))
    print(f"✅ Mapped @{handle} to Game 822957 in m2m_persona_room")

    con.commit()
    con.close()
    print("🏆 Onboarding complete!")

if __name__ == "__main__":
    onboard()
