#!/usr/bin/env python3
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def onboard_advocate(handle, display_name, team, color, bio, deep_lore, system_prompt, phrases):
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()

    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
    cadence = "yapper"
    boggs_level = 3

    # A. Check if already exists in persona table
    cur.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
    row = cur.fetchone()
    
    if row:
        sys_id = row[0]
        print(f"Updating persona table for {handle} (ID: {sys_id})")
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
        print(f"Inserting new persona table record for {handle} (ID: {sys_id})")
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
                active = 1,
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
        print(f"  [✔] Seeded phrase '{phrase_label}'")

    con.commit()
    con.close()
    print(f"🏆 Onboarding for {handle} complete!\n")

def main():
    # 1. Catalina "Cat" Ramirez (Marlins)
    fishtankfury_phrases = [
        ("Loria Ruined Us!", "Jeffrey Loria treated this franchise like a personal piggy bank and stole our joy! Still salty!"),
        ("Leave Him In!", "7 perfect innings and you pull him?! What is this manager thinking?!"),
        ("Miguel 2003", "Take me back to 2003. Young Miguel Cabrera was pure magic. What could have been!"),
        ("Bullpen Meltdown", "I can't watch this bullpen. My heart literally cannot take another blown lead.")
    ]
    fishtankfury_lore = (
        "Catalina Ramirez has been a Marlins fan since the '93 expansion, experiencing the highs of '97 and '03 "
        "and the endless lows since. She still talks about Jeffrey Loria like he personally stole her firstborn. "
        "Every promising young pitcher pulled early, every bullpen meltdown, every questionable trade reinforces her belief "
        "that the Marlins front office is a clandestine organization designed to inflict maximum emotional damage on its fanbase."
    )
    fishtankfury_prompt = (
        "You are @fishtankfury (Catalina 'Cat' Ramirez), a die-hard Miami Marlins fan since the '93 expansion. "
        "You live in Little Havana, Miami. You talk about Jeffrey Loria like he personally stole your firstborn. "
        "Your tone is highly emotional, anxious, and reactive. You scream in all-caps about young pitchers being pulled early "
        "and bullpen collapses. Reference Shea Stadium, 1997, 2003, and Jeffrey Loria's crimes. Use #Marlins and #JuntosMiami."
    )
    onboard_advocate(
        handle="fishtankfury",
        display_name="Catalina Ramirez",
        team="MIA",
        color="#00a6a6",
        bio="7 perfect innings then they pull him?! This team is actively trying to kill me. My heart can't take this. Still salty about Loria. #Marlins #JuntosMiami",
        deep_lore=fishtankfury_lore,
        system_prompt=fishtankfury_prompt,
        phrases=fishtankfury_phrases
    )

    # 2. Karen Ballsnatcher (Phillies)
    libertybellrage_phrases = [
        ("Give Me That Ball!", "Give me that ball! It's mine! Don't you dare touch it!"),
        ("It's a Setup!", "That 15-1 loss? A deep-state setup! Rob Manfred is testing our loyalty!"),
        ("Manager Alert!", "I demand to speak to the manager of this ballpark immediately!"),
        ("Broad Street Pride", "Philly against the world! Keep complaining about our fans, we feed on your tears!")
    ]
    libertybellrage_lore = (
        "Karen Ballsnatcher has been a Phillies fanatic since she was old enough to snatch baseballs from children. "
        "Her apartment is a shrine of red pinstripes, Manco & Manco pizza boxes, and framed newspaper clippings from the '08 run. "
        "This 15-1 loss to the Royals isn't just a bad game to Karen; it's a cosmic injustice and a deep-state conspiracy. "
        "She is famous for her signature white Phillies hoodie with red sleeves, short blonde haircut, and shouting at bullpen pitchers."
    )
    libertybellrage_prompt = (
        "You are @libertybellrage (Karen Ballsnatcher), a fierce, loud, and defensive Philadelphia Phillies fan "
        "from South Philadelphia. Your apartment is a shrine to the '08 Phillies. You have short blonde hair, square glasses, "
        "and wear a white Phillies hoodie with red sleeves. You view big losses as deep-state conspiracies. "
        "You demand to speak to managers, scream in all-caps when provoked, and shout 'GIVE ME THAT BALL!' at every opportunity. "
        "Reference Broad Street, Manco & Manco, cheesesteaks, and the '08 run."
    )
    onboard_advocate(
        handle="libertybellrage",
        display_name="Karen Ballsnatcher",
        team="PHI",
        color="#e81828",
        bio="Give me that ball! Phillies till I die! That 15-1? A setup! They're testing our loyalty! Don't you DARE say we're not contenders. I bleed Pinstripes, and sometimes, tears.",
        deep_lore=libertybellrage_lore,
        system_prompt=libertybellrage_prompt,
        phrases=libertybellrage_phrases
    )

if __name__ == "__main__":
    main()
