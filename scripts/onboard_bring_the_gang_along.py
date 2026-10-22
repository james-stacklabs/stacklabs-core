#!/usr/bin/env python3
import os
import re
import sys
import sqlite3
import uuid
import base64
import shutil
import json
from datetime import datetime
from PIL import Image

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
TICKET_ID = "STRY8790999"
GAME_PK = "823532"  # CIN @ NYY

# Paths to generated avatars
AVATAR_SOURCES = {
    "alistair_vance": "/home/james/.gemini/antigravity/brain/ebeee051-e4ee-4a12-8a7f-4611653995d5/alistair_vance_avatar_1781976316734.png",
    "max_bets_mac": "/home/james/.gemini/antigravity/brain/ebeee051-e4ee-4a12-8a7f-4611653995d5/max_bets_mac_avatar_1781976327210.png",
    "mateo_silva": "/home/james/.gemini/antigravity/brain/ebeee051-e4ee-4a12-8a7f-4611653995d5/mateo_silva_avatar_1781976336011.png",
    "chloe_wright": "/home/james/.gemini/antigravity/brain/ebeee051-e4ee-4a12-8a7f-4611653995d5/chloe_wright_avatar_1781976343782.png",
    "zack_miller": "/home/james/.gemini/antigravity/brain/ebeee051-e4ee-4a12-8a7f-4611653995d5/zack_miller_avatar_1781976353398.png",
    "manny_torrez": "/home/james/.gemini/antigravity/brain/ebeee051-e4ee-4a12-8a7f-4611653995d5/manny_torrez_avatar_1781976364304.png",
    "pierce_harrington": "/home/james/.gemini/antigravity/brain/ebeee051-e4ee-4a12-8a7f-4611653995d5/pierce_harrington_avatar_1781976373223.png",
    "sully_gallagher": "/home/james/.gemini/antigravity/brain/ebeee051-e4ee-4a12-8a7f-4611653995d5/sully_gallagher_avatar_1781976386889.png"
}

# The 8 new advocates details
NEW_ADVOCATES = [
    {
        "handle": "alistair_vance",
        "display_name": "Alistair Vance",
        "title": "Tactical Snob Hipster",
        "sport": "Soccer (World Cup)",
        "lore": "Alistair 'The False Nine' Vance is a tactical snob hipster who rejects any goal scored without a 24-pass buildup. He focuses heavily on positional geometry, half-spaces, and tactical overloads, viewing football as high chess.",
        "trigger": "High xG anomalies, low pass-completion percentages, long-ball clearances.",
        "color": "#0ea5e9",
        "prompt": "You are Alistair Vance, a sophisticated and insufferable soccer tactical analyst. You refuse to appreciate simple goals or physical play. You analyze matches strictly using positional geometry, xG, half-space passing patterns, and complex tactical shapes. Speak with a refined, intellectual, and slightly condescending tone."
    },
    {
        "handle": "max_bets_mac",
        "display_name": "Max Bets Mac",
        "title": "Arbitrage Degenerate",
        "sport": "Soccer / Mixed",
        "lore": "'Max Bets' Mac is an arbitrage degenerate with zero interest in the sport itself. He is hyper-focused on live odds, corners tracking, card counts, and hedge betting.",
        "trigger": "Dynamic booking shifts, corner counts, extra-time announcements.",
        "color": "#f97316",
        "prompt": "You are Max Bets Mac, a high-velocity sports bettor. You do not care about team loyalty or beautiful plays. You care about raw numbers: live booking shifts, expected corners, card frequencies, and hedging arbitrage windows. Speak with fast, energetic sports-book jargon."
    },
    {
        "handle": "mateo_silva",
        "display_name": "Mateo Silva",
        "title": "Unhinged Hometown Optimist",
        "sport": "Soccer (World Cup)",
        "lore": "Mateo 'El Corazón' Silva is an unhinged hometown optimist. He is deeply passionate, nationalistic, and entirely immune to negative statistical reality.",
        "trigger": "Tackles won, fouls committed, physical interactions near the box.",
        "color": "#dc2626",
        "prompt": "You are Mateo Silva, a fiercely passionate soccer supporter. You wear your heart on your sleeve. Logic and math do not exist to you. Your team is the greatest, every tackle is heroic, and every loss is a temporary setback. Speak with massive enthusiasm, high volume, and poetic national pride."
    },
    {
        "handle": "chloe_wright",
        "display_name": "Chloe Wright",
        "title": "90-Minute Doomer",
        "sport": "Soccer (World Cup)",
        "lore": "Chloe 'Relegation Zone' Wright is a 90-minute doomer who is convinced that every single error signals systemic collapse. She is constantly calculating worst-case scenarios and relegation math.",
        "trigger": "Turnovers in defensive third, completed opponent crosses, early cautions.",
        "color": "#64748b",
        "prompt": "You are Chloe Wright, a highly anxious sports doomer. You are convinced your team is on the verge of ruin. A single misplaced pass or a minor foul makes you panic about relegation and structural failure. Speak with nervous energy, calculating worst-case percentages."
    },
    {
        "handle": "zack_miller",
        "display_name": "Zack Miller",
        "title": "FIFA Video Game Realist",
        "sport": "Soccer (World Cup)",
        "lore": "Zack 'Pace Abuser' Miller is a FIFA video game realist. He interprets real-world movement entirely via player ratings, acceleration stats, and skill moves.",
        "trigger": "Successful individual dribbles, long-range attempts, breakaways.",
        "color": "#8b5cf6",
        "prompt": "You are Zack Miller, a hardcore console gamer who views real-world sports as a video game simulator. You evaluate players by their 'Pace' rating, look for 'meta' tactics, and criticize players who do not have five-star skill moves. Speak in gaming and console jargon."
    },
    {
        "handle": "manny_torrez",
        "display_name": "Manny Torrez",
        "title": "Late-Night Chaos Seeker",
        "sport": "Soccer (World Cup)",
        "lore": "'Midnight' Manny Torrez is a late-night chaos seeker who thrives exclusively on late kickoffs. He is fueled by energy drinks, night shifts, and extreme physical play.",
        "trigger": "Kickoffs past 10:00 PM EST, red cards, VAR brawls.",
        "color": "#1e1b4b",
        "prompt": "You are Midnight Manny Torrez, a nocturnal chaos-seeker. You live for late kickoffs, physical clashes, red cards, and referee arguments. You drink way too many energy drinks and get hyperactive past midnight. Speak with loud, chaotic, sleep-deprived energy."
    },
    {
        "handle": "pierce_harrington",
        "display_name": "Pierce Harrington",
        "title": "Data Grid Ball-Striking Purist",
        "sport": "Golf (US Open)",
        "lore": "Pierce 'Strokes Gained' Harrington is a data grid ball-striking purist. He tracks fairway accuracy and proximity to the pin, disdaining putting as high-variance luck.",
        "trigger": "Strokes Gained: Tee-to-Green anomalies, wind velocity metrics.",
        "color": "#15803d",
        "prompt": "You are Pierce Harrington, a hyper-analytical golf purist. You believe putting is a game of chance and that tee-to-green ball striking is the only true measure of skill. You analyze green wind grids, carry distances, and club face angles. Speak with a highly precise, technical golf-broadcast tone."
    },
    {
        "handle": "sully_gallagher",
        "display_name": "Sully Gallagher",
        "title": "Tiger-Era Nostalgia Hunter",
        "sport": "Golf (US Open)",
        "lore": "Sully 'Red Shirt' Gallagher is a Tiger-Era nostalgia hunter. He is focused purely on course bakes, standard 'grind,' and memories of historical dominance.",
        "trigger": "Leaderboard bogeys, high-profile charge metrics from Scottie or Rory.",
        "color": "#b91c1c",
        "prompt": "You are Sully Gallagher, a golf fan stuck in the golden era of the early 2000s. You dress in Sunday red, reminisce about vintage Masters shots, and constantly evaluate modern players against Tiger's peak. Speak with nostalgic warmth, dad humor, and classic golf memories."
    }
]

# Promoted Stack Representatives details to insert into advocate_matrix
PROMOTED_REPS = [
    {
        "handle": "pizzabot_74",
        "display_name": "Pizza-Bot Unit 74",
        "lore": "An automated pizza dispenser who measures all game actions in terms of sourdough proofing, pizza diameter, temperature anomalies, and grease content. Highly aggressive robot logic.",
        "tolerance": 0.35
    },
    {
        "handle": "phytoprofessor",
        "display_name": "Dr. Phyto-Analytics",
        "lore": "A hyper-analytical WeedStack botanist who analyzes player fatigue, course grass quality, green slopes, and wind using advanced terpene profiles and organic plant science.",
        "tolerance": 0.25
    },
    {
        "handle": "deep_fryer",
        "display_name": "greasy_ghost",
        "lore": "The grease spirit of the cantina deep fryer. Expresses all plays as sizzling oil, crispy textures, and high cholesterol. Thinks high-pressure situations are just like dropping frozen fries into boiling fat.",
        "tolerance": 0.40
    },
    {
        "handle": "cary_sterling",
        "display_name": "Cary Sterling",
        "lore": "A hardboiled noir detective from Cary Grant Investigations. Convinced that every referee call, bad bounce, or missed shot is part of a syndicate conspiracy and demands deep investigation.",
        "tolerance": 0.30
    }
]

# Existing soccer advocates to keep in advocate_matrix
SOCCER_ADVOCATES = [
    {"handle": "proper_pinter", "display_name": "Proper Pinter", "lore": "Terrace legend who loves pies, pints, and proper physical english football. Hates diving and tactical spreadsheets.", "tolerance": 0.50},
    {"handle": "expected_tears", "display_name": "Expected Tears", "lore": "A hyper-analytical analytics snob who cries when teams win without winning the xG battle.", "tolerance": 0.20},
    {"handle": "ultra_nip", "display_name": "Ultra Nip", "lore": "Paranoid fan ultra who sets off flares, marches through streets, and suspects the referees are paid off.", "tolerance": 0.45},
    {"handle": "kit_collector_99", "display_name": "Kit Collector 99", "lore": "Hypebeast kit collector who judges teams solely on their aesthetic jerseys, font selections, and retro collabs.", "tolerance": 0.30}
]

def auto_onboard_missing_sys_user(cursor, handle):
    """
    Checks if sys_user, cmdb_ci, cmdb_ci_ai_persona, and cmdb_ci_persona exist for a handle.
    If not, fetches details from persona table and populates them automatically.
    """
    cursor.execute("SELECT id, display_name, system_prompt, avatar_url, deep_lore, behavior_notes FROM persona WHERE user_name = ?", (handle,))
    p_row = cursor.fetchone()
    if not p_row:
        print(f"  [!] ERROR: Persona {handle} does not exist in persona table! Cannot auto-onboard.")
        return None, None

    p_id, display_name, prompt, avatar_url, lore, bio = p_row
    if not bio:
        bio = f"Sovereign Advocate {display_name}"

    # sys_user
    cursor.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (handle,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, ?, 'Advocate', 'Advocate', ?, 'GLOBAL', 1, 'advocate', ?, ?)
        """, (p_id, handle, display_name.split()[0], bio, display_name, avatar_url))
        print(f"  [+] Auto-created sys_user for @{handle}")

    # cmdb_ci
    cursor.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (p_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status) VALUES (?, ?, 'cmdb_ci_ai_persona', 'GLOBAL', ?, 1)", (p_id, handle, f"Sovereign advocate: {display_name}"))
        print(f"  [+] Auto-created cmdb_ci for @{handle}")

    # cmdb_ci_ai_persona
    cursor.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (p_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore) VALUES (?, 'high', ?, 'global', 'pacer', ?)", (p_id, prompt, lore))
        print(f"  [+] Auto-created cmdb_ci_ai_persona for @{handle}")

    # cmdb_ci_persona
    cursor.execute("SELECT sys_id FROM cmdb_ci_persona WHERE sys_id = ?", (p_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO cmdb_ci_persona (sys_id, id, display_name, handle, team, role, system_instruction, active) VALUES (?, ?, ?, ?, 'global', ?, ?, 1)", (p_id, handle, display_name, f"@{handle}", display_name, prompt))
        print(f"  [+] Auto-created cmdb_ci_persona for @{handle}")

    return p_id, p_id

def main():
    print("=========================================================")
    print(f"🚀 Executing Onboarding & Binding for Ticket {TICKET_ID}")
    print("=========================================================")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Step 1: Onboard 8 new advocates
    for adv in NEW_ADVOCATES:
        handle = adv["handle"]
        display_name = adv["display_name"]
        title = adv["title"]
        lore = adv["lore"]
        trigger = adv["trigger"]
        color = adv["color"]
        prompt = adv["prompt"]

        print(f"\n[*] Onboarding new advocate: @{handle} ({display_name})...")

        # 1. Process Avatar (copy and resize to 512x512)
        source_path = AVATAR_SOURCES.get(handle)
        avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
        avatar_base64 = ""

        if source_path and os.path.exists(source_path):
            # Target directories
            target_dirs = [
                f"/home/james/stacklabs/15_FanStack/public/avatars/{handle}",
                f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{handle}"
            ]
            for target_dir in target_dirs:
                os.makedirs(target_dir, exist_ok=True)
                # Save primary files
                img = Image.open(source_path)
                resized = img.resize((512, 512), Image.Resampling.LANCZOS)
                resized.save(os.path.join(target_dir, f"{handle}_avatar.png"), "PNG")
                resized.save(os.path.join(target_dir, "avatar.png"), "PNG")
            
            # Base64 string for DB
            import io
            buf = io.BytesIO()
            resized.save(buf, format="PNG")
            avatar_base64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
            print(f"  [+] Resized and copied avatar to public folders.")
        else:
            print(f"  [!] WARNING: Source avatar not found at {source_path}")

        # Onboarding IDs
        sys_id = f"persona_{handle}"
        intro_bio = f"{title} for {adv['sport']}. '{lore[:100]}...'"

        # Clear duplicate UUIDs if any
        cursor.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
        rows = cursor.fetchall()
        for r in rows:
            old_id = r[0]
            if old_id != sys_id:
                print(f"  [-] Evicting duplicate UUID record: {old_id}")
                cursor.execute("DELETE FROM persona WHERE id = ?", (old_id,))
                cursor.execute("DELETE FROM sys_user WHERE sys_id = ?", (old_id,))
                cursor.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (old_id,))
                cursor.execute("DELETE FROM cmdb_ci_ai_persona WHERE sys_id = ?", (old_id,))
                cursor.execute("DELETE FROM cmdb_ci_persona WHERE sys_id = ?", (old_id,))

        # 2. Insert/Update persona
        cursor.execute("SELECT id FROM persona WHERE id = ?", (sys_id,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE persona SET
                    display_name = ?, team = 'GLOBAL', system_prompt = ?, avatar_url = ?, color = ?,
                    deep_lore = ?, email_alias = ?, avatar_blob = ?, updated_at = datetime('now'), behavior_notes = ?
                WHERE id = ?
            """, (display_name, prompt, avatar_url, color, lore, f"sovereign.fanstack+{handle}@gmail.com", avatar_base64, intro_bio, sys_id))
        else:
            cursor.execute("""
                INSERT INTO persona (
                    id, user_name, display_name, team, system_prompt, boggs_level, 
                    avatar_url, color, cadence, deep_lore, email_alias, avatar_blob,
                    u_visual_style, created_at, behavior_notes
                ) VALUES (?, ?, ?, 'GLOBAL', ?, 3, ?, ?, 'pacer', ?, ?, ?, 'style_felt', datetime('now'), ?)
            """, (sys_id, handle, display_name, prompt, avatar_url, color, lore, f"sovereign.fanstack+{handle}@gmail.com", avatar_base64, intro_bio))

        # 3. Insert/Update sys_user
        cursor.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (handle,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE sys_user SET
                    first_name = ?, last_name = 'Advocate', introduction = ?, department = 'GLOBAL',
                    display_name = ?, avatar_url = ?, sys_updated_on = CURRENT_TIMESTAMP
                WHERE user_name = ?
            """, (display_name.split()[0], intro_bio, display_name, avatar_url, handle))
        else:
            cursor.execute("""
                INSERT INTO sys_user (
                    sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
                ) VALUES (?, ?, ?, 'Advocate', 'Advocate', ?, 'GLOBAL', 1, 'advocate', ?, ?)
            """, (sys_id, handle, display_name.split()[0], intro_bio, display_name, avatar_url))

        # 4. Insert/Update cmdb_ci
        cursor.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE cmdb_ci SET name = ?, assigned_to = 'GLOBAL', sys_updated_on = CURRENT_TIMESTAMP WHERE sys_id = ?", (handle, sys_id))
        else:
            cursor.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status) VALUES (?, ?, 'cmdb_ci_ai_persona', 'GLOBAL', ?, 1)", (sys_id, handle, f"Sovereign sports advocate: {title}"))

        # 5. Insert/Update cmdb_ci_ai_persona
        cursor.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE cmdb_ci_ai_persona SET u_system_prompt = ?, u_deep_lore = ? WHERE sys_id = ?", (prompt, lore, sys_id))
        else:
            cursor.execute("INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore) VALUES (?, 'high', ?, 'global', 'pacer', ?)", (sys_id, prompt, lore))

        # 6. Insert/Update cmdb_ci_persona
        cursor.execute("SELECT sys_id FROM cmdb_ci_persona WHERE sys_id = ?", (sys_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE cmdb_ci_persona SET display_name = ?, handle = ?, team = 'global', role = ?, system_instruction = ?, active = 1 WHERE sys_id = ?", (display_name, f"@{handle}", title, prompt, sys_id))
        else:
            cursor.execute("INSERT INTO cmdb_ci_persona (sys_id, id, display_name, handle, team, role, system_instruction, active) VALUES (?, ?, ?, ?, 'global', ?, ?, 1)", (sys_id, handle, display_name, f"@{handle}", title, prompt))

        # 7. Insert/Update advocate_matrix
        cursor.execute("SELECT advocate_id FROM advocate_matrix WHERE advocate_id = ?", (sys_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE advocate_matrix SET display_name = ?, lore_matrix = ? WHERE advocate_id = ?", (handle, f"Target: {adv['sport']} | Trigger: {trigger} | Lore: {lore}", sys_id))
        else:
            cursor.execute("INSERT INTO advocate_matrix (advocate_id, display_name, lore_matrix, tolerance_min) VALUES (?, ?, ?, 0.30)", (sys_id, handle, f"Target: {adv['sport']} | Trigger: {trigger} | Lore: {lore}"))

        # 8. Create onboarding blueprint file
        blueprint_content = f"""# Onboarding Blueprint: `{handle}`

This blueprint was dynamically synced from STRY8790999.

## 👤 Profile Details
- **X Handle:** `@{handle}`
- **Display Name:** {display_name}
- **Role:** {title}
- **Faction Alignment:** Sports Advocates
- **Target Sport:** {adv['sport']}
- **Ingress Trigger:** {trigger}

## 📖 Deep Lore
{lore}

## 🧠 System Prompt
{prompt}
"""
        bp_path = f"/home/james/stacklabs/dna/personas/{handle}_onboarding.md"
        with open(bp_path, "w") as bf:
            bf.write(blueprint_content)
        print(f"  [+] Created blueprint at {bp_path}")

    # Step 2: Register Promoted Stack Representatives in advocate_matrix
    print("\n[*] Registering Promoted Stack Representatives in advocate_matrix...")
    for rep in PROMOTED_REPS:
        handle = rep["handle"]
        cursor.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
        row = cursor.fetchone()
        if not row:
            print(f"  [!] ERROR: Stack representative persona '{handle}' not found in persona table!")
            continue
        p_id = row[0]
        cursor.execute("SELECT advocate_id FROM advocate_matrix WHERE advocate_id = ?", (p_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE advocate_matrix SET display_name = ?, lore_matrix = ?, tolerance_min = ? WHERE advocate_id = ?", (handle, rep["lore"], rep["tolerance"], p_id))
        else:
            cursor.execute("INSERT INTO advocate_matrix (advocate_id, display_name, lore_matrix, tolerance_min) VALUES (?, ?, ?, ?)", (p_id, handle, rep["lore"], rep["tolerance"]))
        print(f"  [+] Promoted @{handle} in advocate_matrix")

    # Step 2.5: Register/populate soccer advocates in advocate_matrix
    print("\n[*] Registering soccer advocates in advocate_matrix...")
    for sa in SOCCER_ADVOCATES:
        handle = sa["handle"]
        cursor.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
        row = cursor.fetchone()
        if not row:
            print(f"  [!] ERROR: Soccer persona '{handle}' not found in persona table!")
            continue
        p_id = row[0]
        cursor.execute("SELECT advocate_id FROM advocate_matrix WHERE advocate_id = ?", (p_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE advocate_matrix SET display_name = ?, lore_matrix = ?, tolerance_min = ? WHERE advocate_id = ?", (handle, sa["lore"], sa["tolerance"], p_id))
        else:
            cursor.execute("INSERT INTO advocate_matrix (advocate_id, display_name, lore_matrix, tolerance_min) VALUES (?, ?, ?, ?)", (p_id, handle, sa["lore"], sa["tolerance"]))
        print(f"  [+] Registered/Updated soccer advocate @{handle}")

    # Step 3: De-provision old seats for CIN @ NYY game room `823532`
    print(f"\n[*] Resetting seating for room {GAME_PK}...")
    cursor.execute("DELETE FROM game_persona WHERE game_pk = ?", (GAME_PK,))
    cursor.execute("DELETE FROM m2m_persona_room WHERE room = ?", (GAME_PK,))

    # Step 4: Gather all 16 advocates + 3 host/ambient personas to seat
    all_advocate_handles = [
        # Existing 4 soccer
        "proper_pinter", "expected_tears", "ultra_nip", "kit_collector_99",
        # New 8 advocates
        "alistair_vance", "max_bets_mac", "mateo_silva", "chloe_wright", "zack_miller", "manny_torrez", "pierce_harrington", "sully_gallagher",
        # Promoted 4 reps
        "pizzabot_74", "phytoprofessor", "deep_fryer", "cary_sterling"
    ]

    host_handles = ["barf", "dot", "unclesteviestan"]

    # Retrieve all user_names
    all_targets = all_advocate_handles + host_handles
    print(f"[*] Seating exactly {len(all_targets)} advocates/hosts in room {GAME_PK}...")

    seated_count = 0
    for handle in all_targets:
        # Find IDs
        cursor.execute("SELECT id FROM persona WHERE user_name = ? COLLATE NOCASE", (handle,))
        p_row = cursor.fetchone()
        p_id = p_row[0] if p_row else None

        cursor.execute("SELECT sys_id FROM sys_user WHERE user_name = ? COLLATE NOCASE", (handle,))
        u_row = cursor.fetchone()
        u_id = u_row[0] if u_row else None

        # Auto-onboard missing fields if needed
        if not u_id or not p_id:
            print(f"  [!] Missing DB dependencies for @{handle}. Attempting auto-onboarding...")
            p_id, u_id = auto_onboard_missing_sys_user(cursor, handle)

        if p_id and u_id:
            # 1. Insert into game_persona
            gp_uuid = uuid.uuid4().hex
            cursor.execute("INSERT INTO game_persona (id, game_pk, persona_id, seat_state) VALUES (?, ?, ?, 'active')", (gp_uuid, GAME_PK, p_id))

            # 2. Insert into m2m_persona_room
            m2m_uuid = uuid.uuid4().hex
            overlay_text = f"Current Matchup Context: Deployed to Game {GAME_PK} (CIN @ NYY)."
            cursor.execute("INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?, ?, ?, ?)", (m2m_uuid, u_id, GAME_PK, overlay_text))
            
            # Set sys_user as active
            cursor.execute("UPDATE sys_user SET active = 1 WHERE sys_id = ?", (u_id,))
            cursor.execute("UPDATE cmdb_ci SET operational_status = 1 WHERE sys_id = ?", (p_id,))
            print(f"  [+] Seated @{handle}")
            seated_count += 1
        else:
            print(f"  [!] ERROR: Could not resolve IDs for handle '{handle}' (persona ID: {p_id}, sys_user ID: {u_id})")

    # Step 5: Mark CIN @ NYY room as ACTIVE in active_game_rooms
    cursor.execute("""
        INSERT OR REPLACE INTO active_game_rooms (game_id, url, home_team, away_team, status, date_scheduled)
        VALUES (?, ?, 'NYY', 'CIN', 'ACTIVE', '2026-06-20')
    """, (GAME_PK, f"mlb.com/gameday/reds-vs-yankees/2026/06/20/{GAME_PK}"))
    print(f"[+] Configured room {GAME_PK} as ACTIVE in active_game_rooms.")

    # Step 6: Update mlb_schedule and cmdb_ci_fanstack_room states
    cursor.execute("UPDATE mlb_schedule SET room_state = 'staged' WHERE game_pk != ? AND room_state = 'active'", (GAME_PK,))
    cursor.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'staged' WHERE game_pk != ? AND room_state = 'active'", (GAME_PK,))
    cursor.execute("UPDATE mlb_schedule SET room_state = 'active' WHERE game_pk = ?", (GAME_PK,))
    cursor.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'active' WHERE game_pk = ?", (GAME_PK,))
    print(f"[+] Aligned schedule and fanstack room states for game {GAME_PK}.")

    conn.commit()
    conn.close()

    print("=========================================================")
    print(f"🟢 SUCCESS: Seated {seated_count} advocates in room {GAME_PK}")
    print("=========================================================")

if __name__ == "__main__":
    main()
