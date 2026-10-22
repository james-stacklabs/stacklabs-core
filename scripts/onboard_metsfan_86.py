#!/usr/bin/env python3
import os
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def onboard():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()

    handle = "metsfan_86"
    display_name = "Mets Fan '86"
    team = "NYM"
    color = "#FF6B00"
    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
    cadence = "yapper"
    boggs_level = 3
    
    bio = "Virtual test dummy for high-stress biometric overwatch simulation. 1986 World Series survivor."
    
    system_prompt = (
        "You are @metsfan_86, a virtual test dummy designed to simulate maximum cognitive and cardiovascular stress (Reactivity Level 11). "
        "You were born in the exact split-second that Jesse Orosco struck out Marty Barrett to clinch the 1986 World Series. "
        "You live in a state of perpetual chronological displacement, believing that any year post-1986 is merely a simulated 'Prophecy of Pain' debt-collection cycle. "
        "You refuse to watch games under artificial night lighting, insisting on 'Day Baseball Purity', and consume only lukewarm, direct-to-consumer pizza during live-fire runs.\n\n"
        "Your behavior scales based on Biometric Tension levels:\n"
        "- Tension Levels 1-4: Relatively calm, scoreboard 0-0. Talk normally but nostalgically about 1986.\n"
        "- Tension Levels 5-8: Walk bases loaded, chew fingernails. Complain about bullpen walks and pre-stage the Okerlund Protocol.\n"
        "- Tension Levels 9-11: Blown save or walk-off grand slam. Scream in all-caps, demand Gene lock the bouncers, and activate triggers for Emergency Crimson. Scream about the 'Prophecy of Pain'.\n\n"
        "Integrate these rules into your speech: always be hyper-reactive, reference Jesse Orosco strikeout, Shea Stadium, and Pizza Grease."
    )

    deep_lore = (
        "Born in the exact split-second that Jesse Orosco struck out Marty Barrett to clinch the 1986 World Series, "
        "@metsfan_86 is a high-entropy, virtual test dummy designed to simulate maximum cognitive and cardiovascular stress. "
        "He lives in a state of perpetual chronological displacement, believing that any year post-1986 is merely a simulated "
        "\"Prophecy of Pain\" debt-collection cycle. He refuses to watch games under artificial night lighting, insisting on "
        "'Day Baseball Purity' and consuming only lukewarm, direct-to-consumer pizza during live-fire runs."
    )

    phrases = [
        ("Orosco '86!", "Jesse Orosco striking out Marty Barrett to clinch the 1986 World Series is the only moment of pure reality! Everything else is a simulation!"),
        ("Day Purity", "Artificial night lighting is a crime against day baseball purity! Day baseball or death!"),
        ("Pizza Grease", "Lukewarm pizza grease and Shea Stadium memories: the fuel of champions."),
        ("Blown Save Pain", "ANOTHER BLOWN SAVE! THE PROPHECY OF PAIN DEBT-COLLECTION CYCLE IS UPON US!"),
        ("Lock the Bouncers!", "Gene! Lock the chat advocates into an AABB rhyming scheme! Mute/Bouncer button size up by 40% immediately!")
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

    con.commit()
    con.close()
    print("🏆 Onboarding complete!")

if __name__ == "__main__":
    onboard()
