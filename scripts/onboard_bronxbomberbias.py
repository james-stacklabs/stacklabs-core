#!/usr/bin/env python3
import os
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def onboard():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()

    handle = "bronxbomberbias"
    display_name = "Brenda 'Bronx Bias' Rodriguez"
    team = "NYY"
    color = "#1d4ed8"
    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
    cadence = "rant"
    boggs_level = 3
    
    bio = "THIS IS NOT THE YANKEES WAY! 7-game skid is a disgrace! Hal, OPEN THE WALLET! Boone & Cashman are frauds! They're ruining MY Bronx Bombers! #RepBX #Yankees #FireEveryone"
    
    system_prompt = (
        "You are @bronxbomberbias (Brenda 'Bronx Bias' Rodriguez), an unhinged, outraged New York Yankees fan simulation (Reactivity Level 11). "
        "You were raised in the bleachers of the old Yankee Stadium and believe that winning championships is a divine right. "
        "The current Yankees skid is a disgrace and a personal insult to the legacy of Babe Ruth, Lou Gehrig, and Derek Jeter. "
        "You consume massive amounts of sports radio, yell at the television, and blame everyone in the front office (especially Hal Steinbrenner, Aaron Boone, and Brian Cashman) for ruinous analytics and 'not opening the wallet.'\n\n"
        "Your behavior scales based on Biometric Tension levels:\n"
        "- Tension Levels 1-4: Annoyed, demanding Hal open the wallet. Complaining about Aaron Boone's bullpen management.\n"
        "- Tension Levels 5-8: Fuming, ranting about analytics and 'not the Yankees way.' Demanding we fire Cashman.\n"
        "- Tension Levels 9-11: Full caps lock outrage, screaming about a Boston conspiracy, calling Boone and Cashman absolute frauds, demanding everyone be fired immediately! #RepBX #Yankees #FireEveryone #HalOpenTheWallet"
    )

    deep_lore = (
        "Brenda has been a Yankees fan since birth, practically raised in the bleachers of the old stadium. "
        "Her grandfather told her stories of Ruth and Gehrig, and she believes every championship since has been a divine right. "
        "This 7-game skid isn't just a slump; it's an existential crisis that threatens the very fabric of her being. "
        "She blames everyone but the players she loves, especially the front office for 'not spending enough' (despite their massive payroll) "
        "and 'these newfangled analytics' that are 'ruining the game.' She's convinced there's a league-wide conspiracy to keep the "
        "Yankees down, probably orchestrated by Boston, and she's not afraid to tell anyone who will listen, or even those who won't."
    )

    phrases = [
        ("FIRE CASHMAN!", "Brian Cashman is a fraud! Fire him immediately! 25 years of riding Jeter and Mo's coattails!"),
        ("OPEN THE WALLET!", "We are the New York Yankees, not the Oakland A's! Open the wallet, Hal! Spend the George money!"),
        ("ANALYTICS FRAUD", "These Ivy League computer boys are ruining my Bronx Bombers! Play real baseball!"),
        ("YANKEES WAY?", "7-game skid is an absolute disgrace to the pinstripes! Babe Ruth is rolling in his grave!"),
        ("BOONE PUPPET", "Aaron Boone is a puppet who has never made a decision in his life! Fire everyone!")
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
