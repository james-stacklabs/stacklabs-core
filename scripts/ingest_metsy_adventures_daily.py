#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import uuid
import base64
import shutil
import json
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
TICKET_ID = "WO-2026-031-METSY-ADVENTURES"
MEDIA_DIR = "/home/james/stacklabs/work_orders/spark/media"

AVATAR_DIRS = [
    "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/metsy_smyrna",
    "/home/james/stacklabs/02_Sovereign_Media/public/avatars/metsy_smyrna",
    "/home/james/stacklabs/15_FanStack/public/avatars/metsy_smyrna"
]

SCENARIOS = [
    {
        "num": 15,
        "name": "Raising the Jolly Roger (The Boat Adventure)",
        "file": "[PROCESSED]_boat_adventure.png",
        "expr": "STANCE: COMMAND/DIRECTIVE",
        "vibe": "Gritty neon-grime cartoon action."
    },
    {
        "num": 16,
        "name": "The Fire Pit Stargazer (The Night Recon)",
        "file": "[PROCESSED]_fire_pit_stargazer.png",
        "expr": "PROFILE: AMICABLE / INVESTIGATIVE",
        "vibe": "Cozy night backyard campfire."
    },
    {
        "num": 17,
        "name": "The Leaf Pile Ambush (The Yard Camouflage)",
        "file": "[PROCESSED]_leaf_pile_ambush.png",
        "expr": "STANCE: HOSTILE / PRE-POUNCE",
        "vibe": "Playful cartoon camouflage."
    },
    {
        "num": 18,
        "name": "The Fence Post Lookout (The Smyrna Heights Watch)",
        "file": "[PROCESSED]_fence_post_lookout.png",
        "expr": "STANCE: PATROL",
        "vibe": "High-contrast cartoon sunset."
    },
    {
        "num": 19,
        "name": "The Bird Feeder Stakeout (The Squirrel Treaty)",
        "file": "[PROCESSED]_bird_feeder_stakeout.png",
        "expr": "ACTION: COMMAND/DIRECTIVE (staring down a rival)",
        "vibe": "Funny heist cartoon style."
    }
]

def get_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def get_sha256(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def generate_next_asset_tag(cursor):
    cursor.execute("SELECT asset_tag FROM sys_media_asset")
    rows = cursor.fetchall()
    max_num = 0
    import re
    for row in rows:
        tag = row[0]
        match = re.search(r'FS-MED-(\d+)', tag)
        if match:
            num = int(match.group(1))
            if num < 99999: # Ignore test tags
                if num > max_num:
                    max_num = num
    next_num = max_num + 1
    return f"FS-MED-{next_num:05d}"

def register_asset(cursor, name, file_name, file_path, category):
    size = os.path.getsize(file_path)
    md5 = get_md5(file_path)
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    
    tag = generate_next_asset_tag(cursor)
    sys_id = uuid.uuid4().hex
    mime_type = "image/png"
    
    cursor.execute("""
        INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
    """, (sys_id, tag, name, file_name, file_path, size, mime_type, category, md5, b64))
    print(f"  [+] Registered Asset: {tag} -> {file_path}")
    return tag, md5

def main():
    print("==================================================================")
    print(f"🚀 Initializing Ingestion for Ticket: {TICKET_ID}")
    print("==================================================================")

    # Verify sources exist
    for sc in SCENARIOS:
        src_path = os.path.join(MEDIA_DIR, sc["file"])
        if not os.path.exists(src_path):
            print(f"[-] ERROR: Source file not found at: {src_path}")
            return

    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Step 1: Stage/Initialize Ticket in DB
    print("[*] Staging ticket in database...")
    cursor.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ?", (TICKET_ID,))
    ticket_row = cursor.fetchone()
    if ticket_row:
        ticket_sys_id = ticket_row[0]
        cursor.execute("""
            UPDATE sovereign_tickets 
            SET state = 2, work_notes = work_notes || '\n[Ingest]: Commenced daily ingestion of Metsy adventure assets.' 
            WHERE sys_id = ?
        """, (ticket_sys_id,))
    else:
        ticket_sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes)
            VALUES (?, ?, 'STRY', '🐾 Ingest and Catalog Metsy June 13 Adventures', 'Automated processing and registration of new daily adventure assets for Metsy Smyrna Heights.', 2, 3, 'james', 'DecisionDerby', 'Ticket initialized by daily ingestion script.')
        """, (ticket_sys_id, TICKET_ID))

    cursor.execute("SELECT task_id FROM sys_sdlc_task WHERE task_id = ?", (TICKET_ID,))
    if cursor.fetchone():
        cursor.execute("UPDATE sys_sdlc_task SET state = 'WIP' WHERE task_id = ?", (TICKET_ID,))
    else:
        cursor.execute("""
            INSERT INTO sys_sdlc_task (task_id, task_type, state, module_target, short_description)
            VALUES (?, 'story', 'WIP', 'portal_core', '🐾 Ingest and Catalog Metsy June 13 Adventures')
        """, (TICKET_ID,))
    conn.commit()

    registered_assets_info = []

    for sc in SCENARIOS:
        src_path = os.path.join(MEDIA_DIR, sc["file"])
        sha256 = get_sha256(src_path)
        
        # Step 2: Register in sys_media_asset
        name = f"Metsy Adventure {sc['num']}: {sc['name']}"
        tag, md5 = register_asset(cursor, name, sc["file"], src_path, "Metsy Adventures")
        registered_assets_info.append(f"- {sc['file']}: {tag}")

        # Step 3: Register in cmdb_ci_media_asset (Advocate Expression)
        # We'll map the expression to the slug name of the scenario
        expr_key = sc["file"].replace("[PROCESSED]_", "").replace(".png", "")
        expr_sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT OR REPLACE INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
            VALUES (?, 'metsy', ?, ?, ?)
        """, (expr_sys_id, expr_key, src_path, sha256))
        print(f"  [+] Registered in cmdb_ci_media_asset: advocate=metsy, expression={expr_key}")

        # Step 4: Copy to frontend public avatars
        print(f"  [*] Copying {sc['file']} to frontend directories...")
        for target_dir in AVATAR_DIRS:
            os.makedirs(target_dir, exist_ok=True)
            dest = os.path.join(target_dir, sc["file"].replace("[PROCESSED]_", ""))
            shutil.copy2(src_path, dest)
            print(f"    -> Mapped to: {dest}")

        # Step 5: Write receipt JSON
        receipt_path = os.path.join(MEDIA_DIR, f"{sc['file'].replace('.png', '')}_receipt.json")
        receipt_data = {
            "ticket_id": TICKET_ID,
            "pipeline_id": "sovereign_event_media_v1",
            "scenario_number": sc["num"],
            "scenario_name": sc["name"],
            "expression_reference": sc["expr"],
            "style_anchor": "[PROCESSED]_metsy_pirate.png",
            "vibe": sc["vibe"],
            "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "output_file": sc["file"],
            "md5_hash": md5,
            "sha256_hash": sha256
        }
        with open(receipt_path, 'w') as rf:
            json.dump(receipt_data, rf, indent=2)
        print(f"  [+] Created receipt at {receipt_path}")

    # Step 6: Resolve the ticket in DB
    print("[*] Resolving ticket...")
    work_notes_entry = f"\n[Ingest Complete]: Successfully processed and cataloged 5 new daily adventure files.\n" + "\n".join(registered_assets_info)
    cursor.execute("""
        UPDATE sovereign_tickets 
        SET state = 4, work_notes = work_notes || ? 
        WHERE sys_id = ?
    """, (work_notes_entry, ticket_sys_id))
    cursor.execute("UPDATE sys_sdlc_task SET state = 'RESOLVED' WHERE task_id = ?", (TICKET_ID,))
    conn.commit()
    conn.close()

    print("==================================================================")
    print("🟢 SUCCESS: Daily Metsy Ingestion Complete & Ticket Resolved!")
    print("==================================================================")

if __name__ == "__main__":
    main()
