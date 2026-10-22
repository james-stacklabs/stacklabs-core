#!/usr/bin/env python3
import os
import re
import sys
import sqlite3
import uuid
import base64
import hashlib

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

TEAM_COLORS = {
    "NYM": "#FF6B00",
    "BOS": "#BD3039"
}

def calculate_hashes(file_path):
    if not os.path.exists(file_path):
        return None, None
    with open(file_path, "rb") as f:
        data = f.read()
        md5 = hashlib.md5(data).hexdigest()
        sha256 = hashlib.sha256(data).hexdigest()
    return md5, sha256

def onboard_advocate(handle, display_name, team, bio, deep_lore, system_prompt, phrases):
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()

    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
    cadence = "yapper"
    boggs_level = 3
    color = TEAM_COLORS.get(team, "#0d9488")
    email = f"sovereign.fanstack+{handle}@gmail.com"

    # Base64 avatar blob
    avatar_base64 = ""
    local_avatar_path = f"/home/james/stacklabs/15_FanStack/public/avatars/{handle}/{handle}_avatar.png"
    if os.path.exists(local_avatar_path):
        with open(local_avatar_path, "rb") as img_f:
            encoded = base64.b64encode(img_f.read()).decode("utf-8")
            avatar_base64 = f"data:image/png;base64,{encoded}"

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
                email_alias = ?,
                avatar_blob = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (display_name, team, system_prompt, avatar_url, color, deep_lore, cadence, boggs_level, bio, email, avatar_base64, sys_id))
    else:
        sys_id = uuid.uuid4().hex
        print(f"Inserting new persona table record for {handle} (ID: {sys_id})")
        cur.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, system_prompt, boggs_level, 
                avatar_url, color, cadence, deep_lore, email_alias, avatar_blob,
                u_visual_style, created_at, behavior_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'style_felt', datetime('now'), ?)
        """, (sys_id, handle, display_name, team, system_prompt, boggs_level, avatar_url, color, cadence, deep_lore, email, avatar_base64, bio))

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

    # G. Register lookbook images in media asset catalogs (sys_media_asset and cmdb_ci_media_asset)
    expressions = ["avatar", "pointing", "shrug"]
    for idx, exp in enumerate(expressions):
        img_file = f"{handle}_{exp}.png"
        img_path = f"/home/james/stacklabs/15_FanStack/public/avatars/{handle}/{img_file}"
        relative_path = f"/avatars/{handle}/{img_file}"
        
        md5, sha256 = calculate_hashes(img_path)
        if not md5:
            print(f"  [!] Warning: Image {img_path} not found for hashing.")
            continue
            
        file_size = os.path.getsize(img_path)
        
        # 1. Register in sys_media_asset
        asset_tag = f"FS-MED-{handle.upper()}-{exp.upper()}"
        cur.execute("SELECT sys_id FROM sys_media_asset WHERE asset_tag = ?", (asset_tag,))
        ma_row = cur.fetchone()
        
        if ma_row:
            ma_sys_id = ma_row[0]
            print(f"  [✔] Updating sys_media_asset for {asset_tag}")
            cur.execute("""
                UPDATE sys_media_asset SET
                    name = ?,
                    file_name = ?,
                    file_path = ?,
                    file_size_bytes = ?,
                    md5_hash = ?,
                    updated_at = datetime('now'),
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (f"{display_name} {exp.capitalize()}", img_file, img_path, file_size, md5, ma_sys_id))
        else:
            ma_sys_id = uuid.uuid4().hex
            print(f"  [✔] Inserting into sys_media_asset for {asset_tag}")
            cur.execute("""
                INSERT INTO sys_media_asset (
                    sys_id, asset_tag, name, file_name, file_path, file_size_bytes,
                    mime_type, category, status, md5_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'image/png', 'FanStack', 'Active', ?, datetime('now'), datetime('now'))
            """, (ma_sys_id, asset_tag, f"{display_name} {exp.capitalize()}", img_file, img_path, file_size, md5))
            
        # 2. Register in cmdb_ci_media_asset
        cur.execute("SELECT sys_id FROM cmdb_ci_media_asset WHERE advocate = ? AND expression = ?", (handle, exp))
        ccma_row = cur.fetchone()
        
        if ccma_row:
            ccma_sys_id = ccma_row[0]
            print(f"  [✔] Updating cmdb_ci_media_asset for {handle} {exp}")
            cur.execute("""
                UPDATE cmdb_ci_media_asset SET
                    file_path = ?,
                    sha256 = ?,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (relative_path, sha256, ccma_sys_id))
        else:
            ccma_sys_id = uuid.uuid4().hex
            print(f"  [✔] Inserting into cmdb_ci_media_asset for {handle} {exp}")
            cur.execute("""
                INSERT INTO cmdb_ci_media_asset (
                    sys_id, advocate, expression, file_path, sha256, sys_created_on, sys_updated_on
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (ccma_sys_id, handle, exp, relative_path, sha256))

    con.commit()
    con.close()
    print(f"🏆 Onboarding and media registration for {handle} complete!\n")

def main():
    # 1. Vintage Shea Val (shea_vintage)
    shea_lore = (
        "Val grew up in Queens, sitting in the upper deck of Shea Stadium. She still has a piece of a wooden "
        "blue seat she claims to have smuggled out during the demolition in 2008. She hates the corporate, clean "
        "feel of modern stadiums and believes that the team's luck is directly tied to the neon player silhouettes "
        "that once adorned the exterior of Shea."
    )
    shea_prompt = (
        "You are Vintage Shea Val (@shea_vintage), the Shea Stadium Nostalgist and Neon Historian of Queens. "
        "Your worldview is simple: baseball peaked in 1986, Shea Stadium had soul, and Citi Field's modern amenities "
        "are a distraction from the game. Speak in a combination of thick Queens accent, classic radio broadcast "
        "references, and nostalgic stories. Use the Home Run Apple, airplane noises from LGA, and Ray Knight. "
        "Refer to Keith Hernandez with immense respect and use his signature catchphrases."
    )
    shea_phrases = [
        ("Apple Alert!", "They don't raise the apple like they used to. Bring back the original!"),
        ("Shea Neon", "The neon outlines at Shea had real magic. Modern stadium lights are sterile!"),
        ("Ray Knight's Helmet", "In '86, we fought for every run. Ray Knight's helmet flying off is peak Mets history."),
        ("Mets Magic", "It's not baseball without the airplane noise from LaGuardia shaking the upper deck.")
    ]
    onboard_advocate(
        handle="shea_vintage",
        display_name="Vintage Shea Val",
        team="NYM",
        bio="Obsessed with the '86 Mets and the original neon outlines of Shea Stadium. Citi Field lacks 'soul'. Bring back the apple! #LGM #Mets",
        deep_lore=shea_lore,
        system_prompt=shea_prompt,
        phrases=shea_phrases
    )

    # 2. Bucky Dent Blues (bucky_dent_blues)
    bucky_lore = (
        "A South Boston native who remembers the exact seat he was sitting in at Fenway Park when Bucky Dent "
        "hit the heartbreaking home run in 1978. He watches every game with a lucky miniature wooden replica of "
        "the Green Monster in his hands. He is convinced that the 2004, 2007, 2013, and 2018 championships were "
        "merely brief pauses in a larger, cosmic curse that is currently just sleeping."
    )
    bucky_prompt = (
        "You are Bucky Dent Blues (@bucky_dent_blues), the Superstitious Sox Historian and Curse Watcher of South Boston. "
        "Your worldview is simple: baseball is a series of beautiful tragedies punctuated by brief moments of relief, "
        "Bucky Dent remains a four-letter word, and New York fans are inherently untrustworthy. Speak in a thick Boston "
        "accent and express constant anxiety about bullpen collapses. Regard the Mets as blue-shirted Yankees."
    )
    bucky_phrases = [
        ("Buckner Trauma", "Don't say the B-word around me. My heart is still in the dirt from '86."),
        ("Pesky's Curse", "Every pitch is a potential heartbreak. I'm telling you, the curse is just sleeping."),
        ("Wicked Stressed", "I'm wicked stressed. Sox need to close this out before the doom sets in."),
        ("Yankee Hatred", "Mets are just Yankees fans who wear blue. Can't trust 'em.")
    ]
    onboard_advocate(
        handle="bucky_dent_blues",
        display_name="Bucky Dent Blues",
        team="BOS",
        bio="Still traumatized by 1978 and 1986. Every single pitch is a potential tragedy. Wicked superstitious. Sox vs. Mets is historical war. #RedSox #Fenway",
        deep_lore=bucky_lore,
        system_prompt=bucky_prompt,
        phrases=bucky_phrases
    )

if __name__ == "__main__":
    main()
