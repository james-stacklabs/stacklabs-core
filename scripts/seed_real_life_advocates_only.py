#!/usr/bin/env python3
"""
seed_real_life_advocates_only.py
Seeds the 5 Real-Life Smyrna Advocates into sys_user and persona tables.

Step 1: Real-Life Advocates ONLY.
Step 2: Deep Lore Engine will run on these advocates.
Step 3: D&D Characters will be generated FROM their Deep Lore!
"""

import sqlite3
import uuid
import shutil
import os
import hashlib

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

conn = sqlite3.connect(DB_PATH, timeout=10.0)
conn.execute("PRAGMA journal_mode=WAL;")
cur = conn.cursor()

print("🧹 Cleaning up non-compliant persona entries...")
cur.execute("DELETE FROM sys_user WHERE user_name = 'zrobs_the_cruel'")
cur.execute("DELETE FROM persona WHERE user_name = 'zrobs_the_cruel'")
cur.execute("DELETE FROM m2m_persona_room WHERE persona = 'zrobs_the_cruel'")

# Ensure avatar public directory exists for fast UI serving
AVATAR_DIR = "/home/james/stacklabs/01_Sovereign_Portal/public/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)

# Define the 5 Real-Life Advocates
REAL_LIFE_ADVOCATES = [
    {
        "user_name": "clerk_bob",
        "display_name": "Clerk Bob",
        "title": "3rd-Shift Stop-and-Go Clerk",
        "role": "Advocate",
        "team": "TTRPG_Advocates",
        "real_world_bio": "Mild-mannered 3rd-shift clerk at the Smyrna Stop-and-Go on Cobb Parkway. Deals with broken Slushie machines, late-night lottery buyers, and quiet sighing behind bulletproof glass.",
        "avatar_src": "/home/james/.gemini/antigravity/brain/8b497c8a-d84e-485b-b278-328be59752d2/lookbook_clerk_bob_real_life_1787456206865.png"
    },
    {
        "user_name": "catnip_greta",
        "display_name": "Greta",
        "title": "AetherVet Smyrna Receptionist",
        "role": "Advocate",
        "team": "AETHERVET",
        "real_world_bio": "Assistant Manager and Cat Whisperer at AetherVet Smyrna. Warm, soft-spoken, secretly overrides keycards to smuggle calming cat pheromone sprays.",
        "avatar_src": "/home/james/.gemini/antigravity/brain/8b497c8a-d84e-485b-b278-328be59752d2/lookbook_greta_real_life_1787456234469.png"
    },
    {
        "user_name": "aether_drroxy",
        "display_name": "Dr. Roxy",
        "title": "Founder & Lead Clinician (UGA DVM 1983)",
        "role": "Advocate",
        "team": "AETHERVET",
        "real_world_bio": "Founder & Lead Clinician at AetherVet Smyrna. UGA DVM 1983 graduate, Wednesday night league bowler, straight shooter who fixes animals with surgical precision.",
        "avatar_src": "/home/james/.gemini/antigravity/brain/8b497c8a-d84e-485b-b278-328be59752d2/lookbook_dr_roxy_real_life_1787456266248.png"
    },
    {
        "user_name": "barb_founder",
        "display_name": "Barb",
        "title": "Sanctuary Founder & Artist",
        "role": "Advocate",
        "team": "WILD_PAWS",
        "real_world_bio": "Founder of Wild Paws Art Rescue. Tough, sweet Moscato drinker, paint-splattered denim, CCR lover who breaks up dog fights with loud clapping.",
        "avatar_src": "/home/james/.gemini/antigravity/brain/8b497c8a-d84e-485b-b278-328be59752d2/lookbook_dr_roxy_real_life_1787456266248.png"  # fallback if needed
    },
    {
        "user_name": "barf_prime",
        "display_name": "Barf Prime",
        "title": "Mog Security Advocate",
        "role": "Advocate",
        "team": "NYM",
        "real_world_bio": "Spaceballs-style half-man half-dog creative agitator and Mog Security officer. Manic beats, wraps complex systems telemetry in improvised rap bars.",
        "avatar_src": "/home/james/.gemini/antigravity/brain/8b497c8a-d84e-485b-b278-328be59752d2/lookbook_barf_prime_real_life_1787456298927.png"
    }
]

print("⚡ Seeding Real-Life Advocates ONLY into sys_user and persona...")

for adv in REAL_LIFE_ADVOCATES:
    # Copy avatar image to public static path & api path
    dest_filename = f"{adv['user_name']}.png"
    dest_path = os.path.join(AVATAR_DIR, dest_filename)
    if os.path.exists(adv['avatar_src']):
        shutil.copy(adv['avatar_src'], dest_path)
    
    avatar_url = f"/avatars/{dest_filename}"

    # A. sys_user table (Real-Life identity)
    cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (adv["user_name"],))
    if cur.fetchone():
        cur.execute("""
            UPDATE sys_user 
            SET display_name = ?, title = ?, introduction = ?, avatar_url = ?, role = ?, active = 1, sys_updated_on = DATETIME('now')
            WHERE user_name = ?
        """, (adv["display_name"], adv["title"], adv["real_world_bio"], avatar_url, adv["role"], adv["user_name"]))
    else:
        cur.execute("""
            INSERT INTO sys_user (sys_id, user_name, display_name, title, introduction, role, avatar_url, active, sys_created_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, DATETIME('now'))
        """, (uuid.uuid4().hex, adv["user_name"], adv["display_name"], adv["title"], adv["real_world_bio"], adv["role"], avatar_url))

    # B. persona table (Real-Life advocate baseline)
    cur.execute("SELECT id FROM persona WHERE user_name = ?", (adv["user_name"],))
    if cur.fetchone():
        cur.execute("""
            UPDATE persona 
            SET display_name = ?, name = ?, team = ?, deep_lore = ?, behavior_notes = ?, avatar_url = ?, sys_updated_on = DATETIME('now')
            WHERE user_name = ?
        """, (adv["display_name"], adv["display_name"], adv["team"], adv["real_world_bio"], adv["title"], avatar_url, adv["user_name"]))
    else:
        cur.execute("""
            INSERT INTO persona (id, user_name, display_name, name, team, deep_lore, behavior_notes, avatar_url, sys_created_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, DATETIME('now'))
        """, (uuid.uuid4().hex, adv["user_name"], adv["display_name"], adv["display_name"], adv["team"], adv["real_world_bio"], adv["title"], avatar_url))

    # C. CMDB media asset mapping
    cur.execute("SELECT sys_id FROM cmdb_ci_media_asset WHERE advocate = ? AND expression = 'real_life'", (adv["user_name"],))
    if not cur.fetchone():
        file_hash = "sha256_placeholder"
        if os.path.exists(dest_path):
            with open(dest_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
        cur.execute("""
            INSERT INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256, sys_created_on)
            VALUES (?, ?, 'real_life', ?, ?, DATETIME('now'))
        """, (uuid.uuid4().hex, adv["user_name"], avatar_url, file_hash))

    print(f"  ✓ Seeded Real-Life Advocate: {adv['display_name']} ({adv['user_name']}) -> {adv['title']}")

conn.commit()
conn.close()

print("\n✅ Real-Life Advocates successfully seeded as clean baselines!")
