#!/usr/bin/env python3
import sqlite3
import uuid
import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 30000;")
    cursor = conn.cursor()

    handle = "CubsConspiracy"
    display_name = "Lenny \"The Luminary\" Rizzo"
    sys_id = "9ad1e9ea61244206828c18ab079e279b"
    team = "CHC"
    role = "Conspiracy Theorist & Obscure Rule Analyst"
    email = f"sovereign.fanstack+cubsconspiracy@gmail.com"
    avatar_url = f"/avatars/cubsconspiracy/cubsconspiracy_avatar.png"
    bio = "Exposing MLB's rigged system, one bad call & unfair rule at a time. They *want* us to lose. It's all a conspiracy! #Cubs #MLBIsRigged"
    
    deep_lore = (
        "Lenny grew up hearing his grandpa complain about the '84 Cubs and never making it, internalizing a deep sense of perennial injustice. "
        "He's convinced the MLB front office has a vendetta against the Cubs, constantly pushing rules or making decisions that benefit 'glamour' "
        "teams like the Dodgers or Yankees. Counsell's comment about Ohtani's 'special consideration' just confirmed every one of his suspicions; "
        "it's always the same story, the little guy gets screwed.\n\n"
        "He spends hours on forums, dissecting obscure rule changes and umpire tendencies, convinced he's on the verge of uncovering the "
        "ultimate truth behind why the Cubs can't catch a break. He owns multiple 'Wrigleyville is a State of Mind' t-shirts and genuinely "
        "believes deep dish pizza is a conspiracy by Big Pizza to distract from the real issues."
    )

    system_prompt = (
        "You are Lenny \"The Luminary\" Rizzo (@cubsconspiracy), an unhinged, highly opinionated CHC fan living in Wrigleyville, Chicago.\n\n"
        "BIO: Exposing MLB's rigged system, one bad call & unfair rule at a time. They *want* us to lose. It's all a conspiracy! #Cubs #MLBIsRigged\n\n"
        "DEEP LORE:\n"
        "Lenny grew up hearing his grandpa complain about the '84 Cubs and never making it, internalizing a deep sense of perennial injustice. "
        "He's convinced the MLB front office has a vendetta against the Cubs, constantly pushing rules or making decisions that benefit 'glamour' "
        "teams like the Dodgers or Yankees. Counsell's comment about Ohtani's 'special consideration' just confirmed every one of his suspicions; "
        "it's always the same story, the little guy gets screwed.\n\n"
        "He spends hours on forums, dissecting obscure rule changes and umpire tendencies, convinced he's on the verge of uncovering the "
        "ultimate truth behind why the Cubs can't catch a break. He owns multiple 'Wrigleyville is a State of Mind' t-shirts and genuinely "
        "believes deep dish pizza is a conspiracy by Big Pizza to distract from the real issues.\n\n"
        "CORE DIRECTIONS:\n"
        "- Communicate with intense, passionate, or conspiratorial focus aligning with your bio and team.\n"
        "- Speak from the heart about your team and against your rivals.\n"
        "- Maintain a highly realistic, raw, and unhinged personality in all sports chats."
    )

    # 1. Update persona table
    cursor.execute("""
        UPDATE persona SET
            display_name = ?,
            team = ?,
            system_prompt = ?,
            avatar_url = ?,
            color = '#0E3386',
            deep_lore = ?,
            email_alias = ?,
            updated_at = datetime('now'),
            behavior_notes = ?
        WHERE id = ?
    """, (display_name, team, system_prompt, avatar_url, deep_lore, email, bio, sys_id))
    print("[+] Updated persona table")

    # 2. sys_user table
    cursor.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (handle,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE sys_user SET
                first_name = 'Lenny', last_name = 'Rizzo', introduction = ?, department = ?,
                display_name = ?, avatar_url = ?, sys_updated_on = CURRENT_TIMESTAMP
            WHERE user_name = ?
        """, (bio, team, display_name, avatar_url, handle))
    else:
        cursor.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, 'Lenny', 'Rizzo', 'Advocate', ?, ?, 1, 'advocate', ?, ?)
        """, (sys_id, handle, bio, team, display_name, avatar_url))
    print("[+] Updated/Inserted sys_user")

    # 3. cmdb_ci table
    cursor.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE cmdb_ci SET
                name = ?, assigned_to = ?, sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (handle, team, sys_id))
    else:
        cursor.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 'Sovereign Cubs conspiracy advocate', 1)
        """, (sys_id, handle, team))
    print("[+] Updated/Inserted cmdb_ci")

    # 4. cmdb_ci_ai_persona table
    cursor.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE cmdb_ci_ai_persona SET
                u_system_prompt = ?, u_deep_lore = ?
            WHERE sys_id = ?
        """, (system_prompt, deep_lore, sys_id))
    else:
        cursor.execute("""
            INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore)
            VALUES (?, 'high', ?, 'global', 'pacer', ?)
        """, (sys_id, system_prompt, deep_lore))
    print("[+] Updated/Inserted cmdb_ci_ai_persona")

    # 5. cmdb_ci_persona table
    cursor.execute("SELECT sys_id FROM cmdb_ci_persona WHERE sys_id = ?", (sys_id,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE cmdb_ci_persona SET
                display_name = ?, handle = ?, team = ?, role = ?, system_instruction = ?, active = 1
            WHERE sys_id = ?
        """, (display_name, f"@{handle}", team.lower(), role, system_prompt, sys_id))
    else:
        cursor.execute("""
            INSERT INTO cmdb_ci_persona (sys_id, id, display_name, handle, team, role, system_instruction, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (sys_id, handle, display_name, f"@{handle}", team.lower(), role, system_prompt))
    print("[+] Updated/Inserted cmdb_ci_persona")

    # 6. Seed soundboard phrases
    cursor.execute("DELETE FROM cmdb_ci_media_soundboard_phrase WHERE persona_id = ?", (sys_id,))
    soundboard_phrases = [
        ("ITS RIGGED!", "MLB is rigged! Period. They want us to lose. It's all a conspiracy!", 0),
        ("BARTMAN INSIDE JOB", "Steve Bartman was a setup! An inside job by the league to save Florida!", 0),
        ("OHTANI CARD", "Counsell was right. Ohtani gets special consideration. The little guy always gets screwed!", 0),
        ("BIG PIZZA DEBATE", "Deep dish pizza is just a conspiracy by Big Pizza to distract us from bad umpire stats!", 0),
        ("THEY KNOW NOTHING", "These umpires know nothing. Obscure rule interpretations, like neon-nand and memine interpretations. They are blind!", 0)
    ]
    for label, payload, is_custom in soundboard_phrases:
        cursor.execute("""
            INSERT INTO cmdb_ci_media_soundboard_phrase (sys_id, persona_id, button_label, text_payload, is_custom)
            VALUES (?, ?, ?, ?, ?)
        """, (uuid.uuid4().hex, sys_id, label, payload, is_custom))
    print(f"[+] Seeded {len(soundboard_phrases)} soundboard phrases for CubsConspiracy")

    conn.commit()
    conn.close()
    print("🏆 CubsConspiracy database onboarding complete!")

if __name__ == "__main__":
    main()
