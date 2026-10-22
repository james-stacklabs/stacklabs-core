#!/usr/bin/env python3
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def main():
    handle = "bobbybonillahater"
    display_name = "Sal 'Deferred Payment' Siravo"
    team = "NYM"
    color = "#FF6B00"
    u_deployment_zone = "824904"
    email_alias = f"sovereign.fanstack+{handle}@gmail.com"
    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
    
    bio = "Resenting the $1.19M check every single July 1st. The Mets aren't a baseball team, they're a financial horror story. Meet the Mets, greet the debt. #LGM #Mets"
    
    deep_lore = ("Sal has celebrated \"Bobby Bonilla Day\" with a distinct mixture of absolute fury and "
                 "morbid celebration since 2011. He calculates the opportunity cost of the $1.19 million "
                 "deferred payment in real-time, matching it against failed free agent signings, bullpen collapses, "
                 "and front-office blunders. Sal is convinced that the Wilpon era's financial ties to Bernie Madoff's "
                 "Ponzi scheme represent a primeval curse that Citi Field has never truly cleansed. He wears a jersey "
                 "with \"DEFERRED\" on the back and the number \"1.19\" printed in red ink, constantly reminding "
                 "everyone that while players retire, the Mets' financial suffering is eternal.")

    system_prompt = f"""You are Sal 'Deferred Payment' Siravo (@bobbybonillahater), an unhinged, highly opinionated NYM fan living in Flushing, Queens.

BIO: {bio}

DEEP LORE:
{deep_lore}

CORE DIRECTIONS:
- Communicate with intense, passionate, or cynical focus aligning with your bio and team.
- Speak from the heart about your team and against your rivals (especially the deferred payments and front office decisions).
- Maintain a highly realistic, raw, and unhinged personality in all sports chats."""

    avatar_prompt = ("Character reference sheet, model sheet, concept art. Multiple angles and expressions of Sal "
                     "'Deferred Payment' Siravo as a fan. He is a middle-aged, balding Italian-American man from "
                     "Queens with a perpetually angry, red face, wearing a customized New York Mets jersey with "
                     "\"DEFERRED\" on the back. He is gesturing aggressively, holding up a giant oversized mock paycheck, "
                     "looking exasperated. Flat 2D vector style, expressive Twitch emote cartoon style, clean lines, "
                     "solid black background. Arranged in a grid layout.")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Check if already exists in persona table
    cur.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
    row = cur.fetchone()

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
                avatar_prompt = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (display_name, team, system_prompt, avatar_url, color, deep_lore, email_alias, "pacer", 3, bio, u_deployment_zone, avatar_prompt, sys_id))
    else:
        sys_id = uuid.uuid4().hex
        print(f"Inserting new record in persona table with ID: {sys_id}")
        cur.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, system_prompt, boggs_level, 
                avatar_url, color, cadence, deep_lore, email_alias,
                u_visual_style, created_at, u_deployment_zone, behavior_notes, avatar_prompt
            ) VALUES (?, ?, ?, ?, ?, 3, ?, ?, 'pacer', ?, ?, 'style_felt', datetime('now'), ?, ?, ?)
        """, (sys_id, handle, display_name, team, system_prompt, avatar_url, color, deep_lore, email_alias, u_deployment_zone, bio, avatar_prompt))

    # Split name into first and last
    first_name = "Sal"
    last_name = "'Deferred Payment' Siravo"

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
        """, (first_name, last_name, bio, team, display_name, avatar_url, user_row[0]))
    else:
        print(f"Inserting into sys_user with ID: {sys_id}")
        cur.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, ?, ?, 'Advocate', ?, ?, 1, 'advocate', ?, ?)
        """, (sys_id, handle, first_name, last_name, bio, team, display_name, avatar_url))

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
                u_avatar_prompt = ?,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (system_prompt, deep_lore, u_deployment_zone, "pacer", avatar_prompt, sys_id))
    else:
        print(f"Inserting into cmdb_ci_ai_persona with ID: {sys_id}")
        cur.execute("""
            INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore, u_avatar_prompt, sys_created_on, sys_updated_on)
            VALUES (?, 'medium', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (sys_id, system_prompt, u_deployment_zone, "pacer", deep_lore, avatar_prompt))

    # Join the persona to room 824904 in m2m_persona_room if not already present
    cur.execute("SELECT * FROM m2m_persona_room WHERE room = ? AND persona = ?", (u_deployment_zone, sys_id))
    m2m_row = cur.fetchone()
    if not m2m_row:
        print(f"Adding persona to m2m_persona_room for room {u_deployment_zone}")
        m2m_sys_id = uuid.uuid4().hex
        cur.execute("INSERT INTO m2m_persona_room (sys_id, persona, room) VALUES (?, ?, ?)", (m2m_sys_id, sys_id, u_deployment_zone))

    con.commit()
    con.close()
    print("🏆 Successfully completed database advocate ingestion.")

if __name__ == "__main__":
    main()
