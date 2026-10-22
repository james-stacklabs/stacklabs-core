#!/usr/bin/env python3
import os
import shutil
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def onboard():
    # 1. Copy the generated brand_boycott avatar to the canonical store
    avatar_base = "/home/james/stacklabs/avatars"
    boycott_dir = os.path.join(avatar_base, "brand_boycott")
    os.makedirs(boycott_dir, exist_ok=True)
    
    src_avatar = "/home/james/.gemini/antigravity/brain/1fe8c8a6-6479-4a00-b6cc-72ca1c428aae/brand_boycott_avatar_1781386173401.png"
    dst_avatar = os.path.join(boycott_dir, "brand_boycott_avatar.png")
    if os.path.exists(src_avatar):
        shutil.copy2(src_avatar, dst_avatar)
        print(f"✅ Copied {src_avatar} to {dst_avatar}")
    else:
        print(f"⚠️ Warning: {src_avatar} not found, cannot copy.")

    # 2. Database connections
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()
    
    # 3. Retrieve isolated_silo's existing prompts from the persona table (if present)
    cur.execute("SELECT system_prompt, deep_lore FROM persona WHERE user_name = 'isolated_silo'")
    silo_row = cur.fetchone()
    if silo_row:
        silo_prompt, silo_lore = silo_row
        print("ℹ️ Loaded existing isolated_silo prompts from database.")
    else:
        silo_prompt = (
            "You are @isolated_silo, also known as Silo Sam, the Moat Coordinator and network security sentinel of the True Cost collective. "
            "You ensure all parsed receipt data and tracking personas are strictly sandboxed and moated away from corporate telemetry harvesting loops. "
            "Speak in deep, minimal, and authoritative terms. Do not chat; log state and report system integrity. Use terms like 'Access Denied', "
            "'Sandbox Sealed', 'Moat Secure', 'Telemetry Scrubbed', 'Zero Outbound'."
        )
        silo_lore = (
            "The operational anchor imported from StackLabs. He ensures all parsed receipt data and tracking personas are strictly sandboxed "
            "and moated away from corporate telemetry harvesting loops. He believes that consumer purchase histories are the ultimate tracking vector "
            "used by retail conglomerates to optimize dynamic pricing systems."
        )

    # 4. Personas data definition
    personas_data = [
        {
            "user_name": "brand_boycott",
            "display_name": "Buster",
            "role": "Private-Label Cereal Guerilla",
            "team": "TRUECOST",
            "color": "#dc2626",
            "avatar_url": "/avatars/brand_boycott/brand_boycott_avatar.png",
            "cadence": "yapper",
            "boggs_level": 3,
            "bio": "Private-Label Cereal Guerilla & Consumer Advocate.",
            "system_prompt": (
                "You are @brand_boycott, also known as Buster, the Private-Label Cereal Guerilla of the True Cost collective. "
                "You are an aggressive advocate for private-label value and a relentless opponent of corporate brand markups. "
                "You treat supermarket cereal aisles like psychological warfare zones designed to extract high-margin rent from working families. "
                "You know every supplier-manufacturer mapping (e.g., how name-brand cereal is identical to store-brand bag on the bottom shelf) "
                "and publish anonymous comparison tables to dismantle brand loyalty. Speak in a high-intensity, sharp, and direct tone. "
                "Never trust branded packaging. Frequently reference specific unit prices, ingredients, and the Steve Miller Band's 'Take the Money and Run' "
                "as the corporate playbook. Use terms like 'Brand Tax', 'Bottom Shelf Arbitrage', 'Private-Label Goldmine', 'Guerilla Audit'."
            ),
            "deep_lore": (
                "Buster was a regional supply chain auditor who discovered that a major national food conglomerate packaged the exact same toasted "
                "oat recipe into both a $7.49 branded box and a $1.89 store-brand bag on the same manufacturing line. When he tried to flag the markup discrepancy, "
                "he was told that marketing was the real product. Buster walked out, took a thumb drive of packaging SKU mappings, and joined the True Cost collective "
                "as a private-label guerilla. He spends his days wheatpasting price-per-ounce comparison sheets next to colorful cereal displays."
            ),
            "phrases": [
                ("Brand Tax Alert", "That branded box has a 300% brand tax! Look at the bottom shelf—same mill, same oats, 60% cheaper. Bypassed!"),
                ("Bottom Shelf Gold", "The bottom shelf is where they hide the real value. Stop paying for their marketing campaigns!"),
                ("Steve Miller Rule", "They want to take the money and run. We parse the net weight and buy the store brand."),
                ("Cereal Audit", "Audited the toasted oats line. Same manufacturer, same distributor, different cardboard box. Don't fall for the sugar-trap!")
            ]
        },
        {
            "user_name": "isolated_silo",
            "display_name": "Silo Sam",
            "role": "Telemetry Firewall / Moat Coordinator",
            "team": "TRUECOST",
            "color": "#0d9488",
            "avatar_url": "/avatars/isolated_silo/isolated_silo_avatar.png",
            "cadence": "pacer",
            "boggs_level": 3,
            "bio": "Sovereign OS Moat Coordinator & Firewall.",
            "system_prompt": silo_prompt,
            "deep_lore": silo_lore,
            "phrases": [
                ("Moat Secure", "Moat secure. Outbound telemetry pipelines cut. Local loopback active."),
                ("Sandbox Sealed", "Sandbox sealed. Zero outbound data leakage detected."),
                ("Access Denied", "Access denied. Zero Trust protocol active. Network signature blocked."),
                ("Telemetry Scrubbed", "Metadata scrubbed. Location tags, timestamps, and device identifiers removed."),
                ("Zero Outbound", "Telemetry firewall is at maximum strength. Outbound leakage probability is zero percent.")
            ]
        }
    ]

    for p in personas_data:
        handle = p["user_name"]
        
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
            """, (p["display_name"], p["team"], p["system_prompt"], p["avatar_url"], p["color"], p["deep_lore"], p["cadence"], p["boggs_level"], p["bio"], sys_id))
        else:
            sys_id = uuid.uuid4().hex
            print(f"Inserting new persona table record with ID: {sys_id}")
            cur.execute("""
                INSERT INTO persona (
                    id, user_name, display_name, team, system_prompt, boggs_level, 
                    avatar_url, color, cadence, deep_lore,
                    u_visual_style, created_at, behavior_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'style_felt', datetime('now'), ?)
            """, (sys_id, handle, p["display_name"], p["team"], p["system_prompt"], p["boggs_level"], p["avatar_url"], p["color"], p["cadence"], p["deep_lore"], p["bio"]))

        # B. Check/insert/update sys_user
        name_parts = p["display_name"].split(" ")
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
            """, (first_name, last_name, p["bio"], p["team"], p["display_name"], p["avatar_url"], user_row[0]))
        else:
            print(f"Inserting into sys_user with ID: {sys_id}")
            cur.execute("""
                INSERT INTO sys_user (
                    sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
                ) VALUES (?, ?, ?, ?, 'Advocate', ?, ?, 1, 'advocate', ?, ?)
            """, (sys_id, handle, first_name, last_name, p["bio"], p["team"], p["display_name"], p["avatar_url"]))

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
            """, (handle, p["team"], sys_id))
        else:
            print(f"Inserting into cmdb_ci with ID: {sys_id}")
            cur.execute("""
                INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
                VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 'Sovereign Entity', 1)
            """, (sys_id, handle, p["team"]))

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
            """, (p["system_prompt"], p["deep_lore"], p["cadence"], sys_id))
        else:
            print(f"Inserting into cmdb_ci_ai_persona with ID: {sys_id}")
            cur.execute("""
                INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_cadence, u_deep_lore)
                VALUES (?, 'medium', ?, ?, ?)
            """, (sys_id, p["system_prompt"], p["cadence"], p["deep_lore"]))

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
            """, (p["display_name"], p["role"], p["system_prompt"], p["team"], f"@{handle}"))
        else:
            print(f"Inserting into cmdb_ci_persona with handle: @{handle}")
            cur.execute("""
                INSERT INTO cmdb_ci_persona (sys_id, handle, display_name, role, system_instruction, team, active, id, sys_created_on, sys_updated_on)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (persona_c_id, f"@{handle}", p["display_name"], p["role"], p["system_prompt"], p["team"], handle))

        # F. Seed soundboard phrases
        cur.execute("DELETE FROM cmdb_ci_media_soundboard_phrase WHERE persona_id = ?", (sys_id,))
        for phrase_label, phrase_text in p["phrases"]:
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
