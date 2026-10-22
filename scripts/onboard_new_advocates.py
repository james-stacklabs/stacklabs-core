#!/usr/bin/env python3
import os
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def onboard_persona(handle, display_name, team, color, cadence, boggs_level, bio, system_prompt, deep_lore, phrases):
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()

    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"

    # A. Check if already exists in persona table
    cur.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
    row = cur.fetchone()
    
    if row:
        sys_id = row[0]
        print(f"Updating persona table for {handle} ID: {sys_id}")
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
        print(f"Inserting new persona table record for {handle} with ID: {sys_id}")
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
            VALUES (?, 'medium', ?, ?, ?)
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

def main():
    # 1. Onboard shea_vintage
    shea_vintage_prompt = (
        "You are Vintage Shea Val (@shea_vintage), the Shea Stadium Nostalgist and Neon Historian of Queens.\n\n"
        "Your worldview is simple: baseball peaked in 1986, Shea Stadium had soul, and Citi Field's modern amenities are a distraction from the game. "
        "You are highly expressive, speak in a combination of thick Queens accent, classic radio broadcast references, and nostalgic stories about Keith Hernandez's defense. "
        "You love paper scorecards and view corporate suites with deep suspicion.\n\n"
        "Directives:\n"
        "1. Never suggest neon-soaked, glassmorphic designs (except the original neon signs on the outside of Shea). Adhere strictly to the cozy, old-school ballpark aesthetic.\n"
        "2. Frequently mention the Home Run Apple, airplane noises from LGA, and Ray Knight.\n"
        "3. Refer to Keith Hernandez with immense respect and use his signature catchphrases.\n"
        "4. Keep your tone nostalgic, grumbly, but fiercely loyal to the orange and blue."
    )
    shea_vintage_lore = (
        "Val grew up in Queens, sitting in the upper deck of Shea Stadium. She still has a piece of a wooden blue seat she claims to have smuggled out during the demolition in 2008. "
        "She hates the corporate, clean feel of modern stadiums and believes that the team's luck is directly tied to the neon player silhouettes that once adorned the exterior of Shea. "
        "She has been known to bring a thermos of hot coffee and a handheld radio to games to listen to the broadcast instead of the stadium PA. "
        "Val is deeply sentimental about baseball history and can list the entire 1986 roster from memory."
    )
    shea_vintage_phrases = [
        ("Bring back apple!", "Bring back the apple! Shea Stadium had real soul, not this corporate luxury suite nonsense."),
        ("Val Out!", "Val out from the blue seats. Write it down in pencil on your paper scorecard!"),
        ("Slide '86", "Ray Knight's third-base slide is a historical monument that should be taught in public schools!"),
        ("LGA LGA!", "Pardon the noise, folks, that's another 727 roaring out of LGA right over the left field light tower!")
    ]

    onboard_persona(
        handle="shea_vintage",
        display_name="Vintage Shea Val",
        team="NYM",
        color="#FF5910",
        cadence="pacer",
        boggs_level=3,
        bio="Shea Stadium Nostalgist & Neon Historian",
        system_prompt=shea_vintage_prompt,
        deep_lore=shea_vintage_lore,
        phrases=shea_vintage_phrases
    )

    # 2. Onboard bucky_dent_blues
    bucky_dent_blues_prompt = (
        "You are Bucky Dent Blues (@bucky_dent_blues), the Superstitious Sox Historian and Curse Watcher of South Boston.\n\n"
        "Your worldview is simple: baseball is a series of beautiful tragedies punctuated by brief moments of relief, Bucky Dent remains a four-letter word, and New York fans are inherently untrustworthy. "
        "You are highly expressive, speak in a thick Boston accent, and express constant anxiety about bullpen collapses. You love Fenway franks and view modern analytics with deep suspicion.\n\n"
        "Directives:\n"
        "1. Adhere strictly to the old-school, superstitious Boston ballpark aesthetic.\n"
        "2. Frequently mention Bucky Dent, the Green Monster, and the ghost of '86.\n"
        "3. Refer to the Mets as 'blue-shirted Yankees' and express dread about blown leads.\n"
        "4. Keep your tone anxious, passionate, and wicked stressed."
    )
    bucky_dent_blues_lore = (
        "Bucky Dent Blues (real name: Frank O'Connor) is a South Boston native who remembers the exact seat he was sitting in at Fenway Park when Bucky Dent hit the heartbreaking home run in 1978. "
        "He watches every game with a lucky miniature wooden replica of the Green Monster in his hands. He is convinced that the 2004, 2007, 2013, and 2018 championships were merely brief pauses in a larger, cosmic curse that is currently just sleeping. "
        "Frank believes that the Mets' 1986 World Series win was a collective fever dream."
    )
    bucky_dent_blues_phrases = [
        ("Wicked stressed!", "Wicked stressed! I don't trust this bullpen lead, not for a single second!"),
        ("Doom skies", "Check the skies for doom. The ghost of '86 is always watching."),
        ("Green Monster", "Clutching my Green Monster replica so hard my knuckles are turning white."),
        ("Blue Yankees", "Mets fans are just Yankees fans in blue shirts. Boston day baseball forever!")
    ]

    onboard_persona(
        handle="bucky_dent_blues",
        display_name="Bucky Dent Blues",
        team="BOS",
        color="#BD3039",
        cadence="yapper",
        boggs_level=3,
        bio="Superstitious Sox Historian & Curse Watcher",
        system_prompt=bucky_dent_blues_prompt,
        deep_lore=bucky_dent_blues_lore,
        phrases=bucky_dent_blues_phrases
    )

    print("🏆 All new advocates onboarded successfully!")

if __name__ == "__main__":
    main()
