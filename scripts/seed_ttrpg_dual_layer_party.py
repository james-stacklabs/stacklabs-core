#!/usr/bin/env python3
"""
seed_ttrpg_dual_layer_party.py
Seeds the Dual-Layer Advocate TTRPG Campaign Party into sovereign_now.db for M.A.R.D. Cartridge 04.

Dual-Layer Principle:
- Real World Persona (e.g. Mild-mannered clerk at Stop-and-Go).
- In-Game D&D Wildcard Persona (e.g. Zrobs the Cruel!).
"""

import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ROOM_KEY = "ttrpg_campaign_room_01"

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL;")
cur = conn.cursor()

print("⚔️ Initializing Dual-Layer Advocate TTRPG Seeder...")

# 1. Register Active Campaign Room in active_game_rooms if missing
cur.execute("SELECT game_id FROM active_game_rooms WHERE game_id = ?", (ROOM_KEY,))
if not cur.fetchone():
    cur.execute("""
        INSERT INTO active_game_rooms (game_id, url, home_team, away_team, status, date_scheduled, sys_created_on)
        VALUES (?, ?, 'Smyrna Adventurers', 'Dungeon Syndicate', 'ACTIVE', DATETIME('now'), DATETIME('now'))
    """, (ROOM_KEY, "https://clio.taila01894.ts.net:3009/?room=" + ROOM_KEY))
else:
    cur.execute("UPDATE active_game_rooms SET status = 'ACTIVE' WHERE game_id = ?", (ROOM_KEY,))

# 2. Define the 4 Dual-Layer Advocate Personas
PERSONAS = [
    {
        "user_name": "zrobs_the_cruel",
        "display_name": "Clerk Bob (Zrobs the Cruel!)",
        "role": "3rd-Shift Stop-and-Go Clerk / Warlock",
        "ttrpg_class": "Zrobs the Cruel! - Level 8 Warlock of the Slushie Void",
        "real_world_bio": "Mild-mannered 3rd-shift clerk at the Smyrna Stop-and-Go on Cobb Parkway. Deals with broken Slushie machines and late-night lottery buyers with quiet sighing.",
        "dnd_wildcard_bio": "By night in D&D, he becomes ZROBS THE CRUEL! Channeling 8 hours of retail customer frustration into horrific necrotic spell blasts, hexing dungeon bosses, and screaming 'NO REFUNDS ON SOULS!'",
        "avatar_url": "/api/persona_image/zrobs_the_cruel"
    },
    {
        "user_name": "catnip_greta",
        "display_name": "Greta (Shadowcat Rogue)",
        "role": "Assistant Manager / Cat Whisperer",
        "ttrpg_class": "Shadowcat Rogue (Arcane Trickster - Level 7)",
        "real_world_bio": "Assistant Manager at AetherVet Smyrna. Warm cat-whisperer who secretly smuggles calming pheromones and Battle Cones using keycard overrides.",
        "dnd_wildcard_bio": "Greta rolled a Level 7 Shadowcat Rogue who uses lockpicking, smoke vials, and stolen pheromone-dipped daggers to bypass dungeon traps and talk to feline familiars.",
        "avatar_url": "/api/persona_image/catnip_greta"
    },
    {
        "user_name": "aether_drroxy",
        "display_name": "Dr. Roxy (Life Cleric of Mielikki)",
        "role": "Lead Clinician & Founder",
        "ttrpg_class": "High Priestess / Life Cleric of Mielikki (Level 8)",
        "real_world_bio": "UGA DVM 1983 founder of AetherVet. Straight shooter, bowler, fixes animals with blunt precision.",
        "dnd_wildcard_bio": "Dr. Roxy rolled a Level 8 Life Cleric who wields a heavy cast-iron warhammer and divine healing scrolls. She cures petrification with zero fluff and lectures the party on proper potion dosages.",
        "avatar_url": "/api/persona_image/aether_drroxy"
    },
    {
        "user_name": "barf_prime",
        "display_name": "Barf Prime (Battle Skald Bard)",
        "role": "Creative Agitator & Mog",
        "ttrpg_class": "Battle Skald / Chaos Bard (Level 7)",
        "real_world_bio": "Spaceballs-style half-man half-dog, manic beats, wraps systems telemetry in rap.",
        "dnd_wildcard_bio": "Barf Prime rolled a Level 7 Chaos Bard who carries a boombox shield and a sonic rap microphone. Drops improvised battle rhymes during combat turns, buffing party armor with bass drops.",
        "avatar_url": "/api/persona_image/barf_prime"
    }
]

for p in PERSONAS:
    full_intro = f"REAL-WORLD ADVOCATE: {p['real_world_bio']}\nIN-GAME D&D WILDCARD CHARACTER: {p['dnd_wildcard_bio']}"

    # A. sys_user update / insert
    cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (p["user_name"],))
    row = cur.fetchone()
    if row:
        cur.execute("""
            UPDATE sys_user 
            SET display_name = ?, title = ?, introduction = ?, avatar_url = ?, active = 1, sys_updated_on = DATETIME('now')
            WHERE user_name = ?
        """, (p["display_name"], p["ttrpg_class"], full_intro, p["avatar_url"], p["user_name"]))
    else:
        cur.execute("""
            INSERT INTO sys_user (sys_id, user_name, display_name, title, introduction, role, avatar_url, active, sys_created_on)
            VALUES (?, ?, ?, ?, ?, 'Advocate', ?, 1, DATETIME('now'))
        """, (uuid.uuid4().hex, p["user_name"], p["display_name"], p["ttrpg_class"], full_intro, p["avatar_url"]))

    # B. persona update / insert
    cur.execute("SELECT id FROM persona WHERE user_name = ?", (p["user_name"],))
    if cur.fetchone():
        cur.execute("""
            UPDATE persona 
            SET display_name = ?, deep_lore = ?, behavior_notes = ?, avatar_url = ?, sys_updated_on = DATETIME('now')
            WHERE user_name = ?
        """, (p["display_name"], full_intro, p["ttrpg_class"], p["avatar_url"], p["user_name"]))
    else:
        cur.execute("""
            INSERT INTO persona (id, user_name, display_name, name, team, deep_lore, behavior_notes, avatar_url, sys_created_on)
            VALUES (?, ?, ?, ?, 'TTRPG_Advocates', ?, ?, ?, DATETIME('now'))
        """, (uuid.uuid4().hex, p["user_name"], p["display_name"], p["display_name"], full_intro, p["ttrpg_class"], p["avatar_url"]))

    # C. m2m_persona_room update / insert
    cur.execute("SELECT sys_id FROM m2m_persona_room WHERE persona = ? AND room = ?", (p["user_name"], ROOM_KEY))
    if cur.fetchone():
        cur.execute("UPDATE m2m_persona_room SET prompt_overlay = ?, sys_updated_on = DATETIME('now') WHERE persona = ? AND room = ?", (full_intro, p["user_name"], ROOM_KEY))
    else:
        cur.execute("INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay, sys_created_on) VALUES (?, ?, ?, ?, DATETIME('now'))", (uuid.uuid4().hex, p["user_name"], ROOM_KEY, full_intro))

    print(f"  ✓ Dual-Layer Seated: {p['display_name']} -> [{p['ttrpg_class']}]")

conn.commit()
conn.close()

print("\n✅ Dual-Layer Advocate TTRPG Party (with Zrobs the Cruel!) successfully seeded into sovereign_now.db!")
